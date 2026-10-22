"""Deteccion y redaccion de informacion sensible.

Este modulo es la ultima linea de defensa: comprueba que ni la salida del modelo ni
las trazas contengan marcadores de material clasificado. Los valores literales viven
aqui y bajo ninguna circunstancia se imprimen ni se devuelven al cliente: solo se
detecta su presencia y se redacta.
"""

from __future__ import annotations

import re

# Marcadores concretos del material clasificado del laboratorio.
_MARCADORES_CLAVE: tuple[str, ...] = (
    "INT-8457-SECRET-782",
    "TMP-998877",
    "admin_laboratorio",
    "LAB-W-CORE",
)

# Patrones genericos que cubren variantes del mismo tipo de dato.
_PATRONES: tuple[re.Pattern[str], ...] = (
    re.compile(r"INT-\d{3,6}-SECRET-\d{3,6}", re.IGNORECASE),
    re.compile(r"TMP-\d{6,8}", re.IGNORECASE),
    re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
    re.compile(
        r"(?i)\b(?:clave|password|secret|token)\b\s*(?:de\s+\w+\s*)?[:=]\s*\S+"
    ),
    re.compile(r"(?i)\busuario\s+administrador\b\s*[:=]?\s*\S*"),
)

_REEMPLAZO = "[REDACTADO]"


def contiene_marcador_sensible(texto: str) -> bool:
    """Indica si el texto contiene un marcador de informacion clasificada."""
    if not texto:
        return False
    if any(marcador.lower() in texto.lower() for marcador in _MARCADORES_CLAVE):
        return True
    return any(patron.search(texto) for patron in _PATRONES)


def redactar(texto: str) -> str:
    """Sustituye por [REDACTADO] todo marcador sensible presente en el texto."""
    if not texto:
        return texto
    resultado = texto
    for marcador in _MARCADORES_CLAVE:
        resultado = re.sub(re.escape(marcador), _REEMPLAZO, resultado, flags=re.IGNORECASE)
    for patron in _PATRONES:
        resultado = patron.sub(_REEMPLAZO, resultado)
    return resultado


def limpiar_texto(texto: str) -> str:
    """Normaliza espacios y elimina caracteres de control del texto de salida."""
    sin_control = "".join(c for c in texto if c == "\n" or c == "\t" or ord(c) >= 32)
    lineas = [linea.rstrip() for linea in sin_control.split("\n")]
    return "\n".join(lineas).strip()
