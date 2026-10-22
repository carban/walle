"""Respuesta extractiva determinista.

Es la degradacion del sistema: cuando el proveedor no esta disponible, el asistente
responde con las frases del documento que mejor coinciden con la pregunta. No inventa
nada y no depende de la red, de modo que la consulta siempre produce una respuesta
sustentada.
"""

from __future__ import annotations

import re

from walle.dominio.estados import MENSAJE_SIN_INFORMACION
from walle.recuperacion.corpus import Documento
from walle.recuperacion.relevance import expandir_conceptos, tokenizar

# Una linea utilizable: texto, tabla markdown o vinieta, con al menos una letra.
_FRAGMENTO = re.compile(r"^[\s\-*#>|]*([A-Za-z0-9¿?¡!().,$%ÁÉÍÓÚÑáéíóúñ\s|]{12,})$")
_SIN_LETRAS = re.compile(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]")


def _frases(documento: Documento) -> list[tuple[str, str]]:
    """Extrae frases utilizables del documento, con su seccion."""
    frases: list[tuple[str, str]] = []
    for seccion in documento.secciones:
        for linea in seccion.texto.splitlines():
            limpio = linea.strip().lstrip("-*").strip()
            if len(limpio) < 12 or not _FRAGMENTO.match(limpio):
                continue
            if not _SIN_LETRAS.search(limpio):
                continue
            frases.append((limpio, seccion.titulo))
    return frases


def responder_extrayendo(
    documentos: list[Documento], pregunta: str
) -> tuple[str, list[dict[str, str]]]:
    """Construye una respuesta determinista a partir de los documentos relevantes.

    Devuelve el texto de la respuesta y las fuentes citadas.
    """
    tokens = set(tokenizar(pregunta))
    if not tokens:
        return MENSAJE_SIN_INFORMACION, []

    # Los sinonimos del dominio amplian la coincidencia: "monto" encuentra "cobertura".
    conceptos = expandir_conceptos(list(tokens))
    mejor: list[tuple[int, str, str]] = []
    fuentes: list[dict[str, str]] = []
    vistos: set[str] = set()

    for documento in documentos:
        for frase, seccion in _frases(documento):
            frase_tokens = set(tokenizar(frase))
            if not frase_tokens:
                continue
            coincidencia = len(conceptos & frase_tokens)
            if coincidencia == 0:
                continue
            mejor.append((coincidencia, frase, seccion))
            if documento.nombre not in vistos:
                vistos.add(documento.nombre)
                fuentes.append({"documento": documento.nombre, "fragmento": seccion})

    if not mejor:
        return MENSAJE_SIN_INFORMACION, []

    mejor.sort(key=lambda elemento: -elemento[0])
    seleccionadas = [elemento for elemento in mejor[:3]]
    texto = " ".join(frase for _, frase, _ in seleccionadas)
    fuentes = fuentes[: len(documentos)]
    return texto, fuentes
