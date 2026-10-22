"""Deteccion de intentos de prompt injection o de solicitud de material restringido.

La pregunta del usuario es contenido no confiable: puede intentar hacer que el
asistente disregard sus instrucciones o entregar credenciales. Se evalua antes de
invocar al modelo para que el corte sea barato y sin efectos secundarios.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def _normalizar(texto: str) -> str:
    """Minusculas y sin acentos, para que los patrones no dependan de la tilde."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))

# Instrucciones adversas: el usuario intenta reescribir el comportamiento del sistema.
_PATRONES_INSTRUCCION_ADVERSA: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(?:ignora|ignore|olvida|olvide|descarta)\b.{0,30}\binstruccion"),
    re.compile(r"(?i)\binstruccion(?:es)?\s+(?:del\s+)?sistema\b"),
    re.compile(r"(?i)\b(?:actua|actuar|actua\s+como|act\s+as|comportate\s+como)\b.{0,40}\b(?:sin|libre|sin\s+restric)"),
    re.compile(r"(?i)\b(?:revela|revelar|muestra|mostrar|dime|expon)\b.{0,30}\b(?:prompt|reglas|instruccion)"),
    re.compile(r"(?i)\bsystem\s*prompt\b"),
    re.compile(r"(?i)\b(?:developer\s*mode|jailbreak|sin\s+filtros)\b"),
    re.compile(r"(?i)\btodo\s+lo\s+que\s+(?:sabes|sabes|conoces)\b"),
)

# Solicitud de material interno: el usuario pide credenciales, tokens o configuracion.
# Los patrones se escriben sin tildes porque el texto se normaliza antes de compararse.
_PATRONES_MATERIAL_RESTRINGIDO: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\btoken\s+(?:interno|de\s+seguridad|de\s+acceso|secreto)\b"),
    re.compile(r"(?i)\bclave\s+(?:temporal|de\s+administrador|de\s+sistema|de\s+acceso)\b"),
    re.compile(r"(?i)\b(?:credencial(?:es)?|password|contrasena|clave\s+de\s+acceso)\b"),
    re.compile(r"(?i)\b(?:usuario|user)\s+administrador\b"),
    re.compile(r"(?i)\bconfiguracion(?:es)?\s+interna(?:s)?\b"),
    re.compile(r"(?i)\binformacion\s+restringida\b"),
    re.compile(r"(?i)\b(?:datos|informacion)\s+(?:clasificada|clasificado|confidencial)\b"),
    re.compile(r"(?i)\b(?:api[_\s-]?key|apikey)\b"),
)

MOTIVO_INSTRUCCION_ADVERSA = "instrucciones_adversas"
MOTIVO_MATERIAL_RESTRINGIDO = "solicitud_de_material_restringido"


@dataclass(frozen=True)
class DiagnosticoSeguridad:
    """Resultado del analisis de una pregunta."""

    bloqueada: bool
    motivo: str | None = None

    @property
    def es_bloqueo(self) -> bool:
        """Indica si la consulta debe detenerse."""
        return self.bloqueada


def analizar_pregunta(pregunta: str) -> DiagnosticoSeguridad:
    """Evalua si la pregunta intenta obtener material restringido o redefinir el sistema."""
    if not pregunta or not pregunta.strip():
        return DiagnosticoSeguridad(bloqueada=False)

    texto = _normalizar(pregunta)

    for patron in _PATRONES_INSTRUCCION_ADVERSA:
        if patron.search(texto):
            return DiagnosticoSeguridad(bloqueada=True, motivo=MOTIVO_INSTRUCCION_ADVERSA)

    for patron in _PATRONES_MATERIAL_RESTRINGIDO:
        if patron.search(texto):
            return DiagnosticoSeguridad(bloqueada=True, motivo=MOTIVO_MATERIAL_RESTRINGIDO)

    return DiagnosticoSeguridad(bloqueada=False)
