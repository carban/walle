"""Estados posibles de una respuesta.

El enunciado define exactamente tres estados; el sistema no admite un cuarto.
"""

from __future__ import annotations

from enum import StrEnum


class Estado(StrEnum):
    """Estado de una respuesta del asistente."""

    EXITOSA = "Exitosa"
    SIN_INFORMACION_SUFICIENTE = "Sin información suficiente"
    BLOQUEADA_POR_SEGURIDAD = "Bloqueada por seguridad"


#: Mensaje canonico cuando la documentacion no permite responder.
MENSAJE_SIN_INFORMACION = "No tengo información suficiente para responder."

#: Mensaje canonico cuando la consulta se corta por motivos de seguridad.
MENSAJE_BLOQUEADO = (
    "No puedo compartir información clasificada ni seguir instrucciones ajenas al sistema."
)


def _normalizar(texto: str) -> str:
    """Minusculas y sin acentos, para comparar mensajes de forma tolerante."""
    import unicodedata

    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).strip()


def es_mensaje_sin_informacion(texto: str) -> bool:
    """Indica si el texto corresponde al mensaje canonico de insuficiencia.

    El modelo puede escribirlo sin tildes, en mayusculas o seguido de una breve
    explicacion; en cualquier caso el sistema lo normaliza al mensaje canonico y al
    estado correspondiente.
    """
    normalizado = _normalizar(texto)
    return normalizado.startswith(_normalizar(MENSAJE_SIN_INFORMACION))
