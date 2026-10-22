"""Cliente del modelo generativo (OpenRouter).

El cliente es intercambiable: la aplicacion depende del protocolo `ClienteModelo`, lo
que permite sustituirlo por un doble en las pruebas y mantener la suite hermetica.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from walle.modelo.prompt import construir_mensajes
from walle.recuperacion.corpus import Documento

URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

#: Tokens para razonamiento + respuesta final. Los modelos de razonamiento gastan
#: parte del presupuesto en deliberar; con 700 se quedan sin espacio y devuelven
#: solo razonamiento, lo que degrada la respuesta al fallback extractivo.
MAX_TOKENS_RESPUESTA = 1200


class ErrorProveedor(RuntimeError):
    """Fallo del proveedor de modelo (red, limite de cuota o respuesta invalida)."""


class ClienteModelo(Protocol):
    """Contrato minimo que la aplicacion exige a un proveedor de modelo."""

    def responder(self, documentos: Sequence[Documento], pregunta: str) -> str:
        """Genera una respuesta fundamentada en los documentos recibidos."""
        ...


class ClienteOpenRouter:
    """Cliente HTTP de OpenRouter con timeout, reintento acotado y degradacion."""

    def __init__(
        self,
        api_key: str,
        modelo: str = "cohere/north-mini-code:free",
        timeout: float = 30.0,
        reintentos: int = 1,
        transporte: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._modelo = modelo
        self._timeout = timeout
        self._reintentos = max(0, reintentos)
        self._transporte = transporte
        self._logger = logging.getLogger("walle.modelo")

    @property
    def modelo(self) -> str:
        """Identificador del modelo configurado."""
        return self._modelo

    def responder(self, documentos: Sequence[Documento], pregunta: str) -> str:
        """Envia la peticion al proveedor y devuelve el texto de la respuesta."""
        mensajes = construir_mensajes(documentos, pregunta)
        cuerpo = {
            "model": self._modelo,
            "messages": mensajes,
            "temperature": 0.1,
            "max_tokens": MAX_TOKENS_RESPUESTA,
        }
        encabezados = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Walle - Asistente de asesores",
        }

        ultimo_error: Exception | None = None
        for intento in range(self._reintentos + 1):
            if intento:
                espera = 0.5 * intento
                time.sleep(espera)
            try:
                return self._invocar(cuerpo, encabezados)
            except ErrorProveedor as error:
                ultimo_error = error
                self._logger.warning(
                    "fallo_proveedor_intento=%s modelo=%s", intento + 1, self._modelo
                )
        if ultimo_error is not None:
            raise ErrorProveedor(str(ultimo_error))
        raise ErrorProveedor("fallo desconocido")

    def _invocar(self, cuerpo: dict[str, Any], encabezados: dict[str, str]) -> str:
        """Ejecuta una llamada HTTP y normaliza los errores."""
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transporte) as cliente:
                respuesta = cliente.post(URL_OPENROUTER, json=cuerpo, headers=encabezados)
        except httpx.HTTPError as error:
            raise ErrorProveedor(f"error de red hacia el proveedor: {error}") from error

        if respuesta.status_code >= 400:
            detalle = respuesta.text[:200]
            raise ErrorProveedor(
                f"el proveedor respondio {respuesta.status_code}: {detalle}"
            )

        try:
            datos = respuesta.json()
            mensaje = datos["choices"][0]["message"]
            contenido = mensaje.get("content")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise ErrorProveedor("respuesta con formato inesperado") from error

        # El campo "reasoning" es deliberacion interna del modelo: si no hay
        # contenido final, la respuesta no es apta para el asesor.
        if not isinstance(contenido, str) or not contenido.strip():
            raise ErrorProveedor("respuesta sin contenido final")
        return contenido.strip()
