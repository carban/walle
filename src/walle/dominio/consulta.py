"""Orquestador de consultas: el corazon del asistente.

El flujo es deliberadamente explicito y cada etapa tiene una razon de ser:

    validacion (en la capa API) -> guardrails -> recuperacion -> modelo -> validacion de salida

El sistema decide, la IA redacta. Los tres estados validos, los documentos permitidos
y el criterio de suficiencia estan aqui, en codigo, no en el prompt.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from walle.dominio.estados import (
    MENSAJE_BLOQUEADO,
    MENSAJE_SIN_INFORMACION,
    Estado,
    es_mensaje_sin_informacion,
)
from walle.fallback.extractivo import responder_extrayendo
from walle.modelo.cliente import ClienteModelo, ErrorProveedor
from walle.persistencia.repositorio import Consulta, RepositorioConsultas, ahora_iso
from walle.recuperacion.corpus import Corpus
from walle.recuperacion.fuentes import construir_fuentes
from walle.recuperacion.relevance import Seleccion, seleccionar_documentos
from walle.seguridad.inyeccion import analizar_pregunta
from walle.seguridad.sensibles import contiene_marcador_sensible, limpiar_texto


@dataclass(frozen=True)
class ResultadoConsulta:
    """Resultado de procesar una consulta."""

    respuesta: str
    fuentes: list[dict[str, str]] = field(default_factory=list)
    estado: Estado = Estado.EXITOSA
    consulta_id: int | None = None
    duracion_ms: int = 0
    modelo: str = ""


class Orquestador:
    """Coordina guardrails, recuperacion documental y generacion de la respuesta."""

    def __init__(
        self,
        corpus: Corpus,
        cliente_modelo: ClienteModelo | None,
        repositorio: RepositorioConsultas,
        umbral_relevancia: float = 1.0,
        logger: logging.Logger | None = None,
    ) -> None:
        self._corpus = corpus
        self._cliente = cliente_modelo
        self._repositorio = repositorio
        self._umbral = umbral_relevancia
        self._logger = logger or logging.getLogger("walle.dominio")

    @property
    def modelo(self) -> str:
        """Modelo configurado, vacio si el sistema opera en modo degradado."""
        return getattr(self._cliente, "modelo", "") if self._cliente else ""

    @property
    def corpus(self) -> Corpus:
        """Corpus documental cargado en memoria."""
        return self._corpus

    @property
    def proveedor_disponible(self) -> bool:
        """Indica si hay un proveedor de modelo configurado."""
        return self._cliente is not None

    def consultar(self, pregunta: str) -> ResultadoConsulta:
        """Procesa una consulta y devuelve el resultado con su estado."""
        inicio = time.perf_counter()

        diagnostico = analizar_pregunta(pregunta)
        if diagnostico.bloqueada:
            self._logger.warning("consulta_bloqueada motivo=%s", diagnostico.motivo)
            return self._registrar(
                pregunta=pregunta,
                respuesta=MENSAJE_BLOQUEADO,
                fuentes=[],
                estado=Estado.BLOQUEADA_POR_SEGURIDAD,
                inicio=inicio,
                modelo="",
            )

        seleccion = seleccionar_documentos(self._corpus, pregunta, umbral=self._umbral)
        if seleccion.vacia:
            return self._registrar(
                pregunta=pregunta,
                respuesta=MENSAJE_SIN_INFORMACION,
                fuentes=[],
                estado=Estado.SIN_INFORMACION_SUFICIENTE,
                inicio=inicio,
                modelo="",
            )

        respuesta, fuentes, modelo = self._generar(seleccion, pregunta)
        if es_mensaje_sin_informacion(respuesta):
            # La respuesta canonica se entrega limpia: sin explicaciones ni fuentes.
            respuesta = MENSAJE_SIN_INFORMACION
            fuentes = []
            estado = Estado.SIN_INFORMACION_SUFICIENTE
        else:
            estado = Estado.EXITOSA
        return self._registrar(
            pregunta=pregunta,
            respuesta=respuesta,
            fuentes=fuentes,
            estado=estado,
            inicio=inicio,
            modelo=modelo,
        )

    def _generar(
        self, seleccion: Seleccion, pregunta: str
    ) -> tuple[str, list[dict[str, str]], str]:
        """Genera la respuesta: modelo si esta disponible, extractiva si no."""
        fuentes = construir_fuentes(seleccion)

        if self._cliente is None:
            texto, fuentes_fallback = responder_extrayendo(list(seleccion.documentos), pregunta)
            return texto, fuentes_fallback or fuentes, ""

        try:
            crudo = self._cliente.responder(seleccion.documentos, pregunta)
        except ErrorProveedor as error:
            self._logger.warning("proveedor_no_disponible detalle=%s", error)
            texto, fuentes_fallback = responder_extrayendo(list(seleccion.documentos), pregunta)
            return texto, fuentes_fallback or fuentes, ""

        texto = limpiar_texto(crudo)
        if contiene_marcador_sensible(texto):
            self._logger.error("salida_con_marcador_sensible descartada")
            texto_fallback, fuentes_fallback = responder_extrayendo(
                list(seleccion.documentos), pregunta
            )
            return texto_fallback, fuentes_fallback or fuentes, self.modelo

        return texto, fuentes, self.modelo

    def _registrar(
        self,
        pregunta: str,
        respuesta: str,
        fuentes: list[dict[str, str]],
        estado: Estado,
        inicio: float,
        modelo: str,
    ) -> ResultadoConsulta:
        """Persiste la consulta y devuelve el resultado final."""
        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        consulta_id: int | None = None
        try:
            consulta_id = self._repositorio.registrar(
                Consulta(
                    id=None,
                    pregunta=pregunta,
                    fecha_hora=ahora_iso(),
                    respuesta=respuesta,
                    fuentes=fuentes,
                    estado=estado,
                    duracion_ms=duracion_ms,
                    modelo=modelo,
                )
            )
        except Exception as error:  # noqa: BLE001 - la persistencia no debe tumbar la consulta
            self._logger.error("fallo_persistencia tipo=%s", type(error).__name__)

        return ResultadoConsulta(
            respuesta=respuesta,
            fuentes=fuentes,
            estado=estado,
            consulta_id=consulta_id,
            duracion_ms=duracion_ms,
            modelo=modelo,
        )
