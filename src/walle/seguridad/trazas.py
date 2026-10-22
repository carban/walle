"""Trazas estructuradas con identificador de correlacion y redaccion de secretos.

La constitution (seccion 7) exige que cada consulta deje rastro y que ninguna traza
contenga informacion sensible. Este modulo concentra ambas garantias.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from walle.seguridad.sensibles import redactar

_CORRELACION: ContextVar[str | None] = ContextVar("walle_correlacion", default=None)

_CAMPOS_SENSIBLES = (
    "api_key",
    "apikey",
    "authorization",
    "token",
    "clave",
    "password",
    "secret",
)


def nueva_correlacion() -> str:
    """Genera un identificador de correlacion corto y unico."""
    import uuid

    return uuid.uuid4().hex[:12]


def obtener_correlacion() -> str | None:
    """Devuelve el identificador de correlacion de la peticion en curso."""
    return _CORRELACION.get()


@contextmanager
def correlacion(identificador: str | None = None) -> Iterator[str]:
    """Establece el identificador de correlacion durante el bloque."""
    valor = identificador or nueva_correlacion()
    token = _CORRELACION.set(valor)
    try:
        yield valor
    finally:
        _CORRELACION.reset(token)


class _FiltroCorrelacion(logging.Filter):
    """Anade el identificador de correlacion a cada registro."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlacion = obtener_correlacion() or "-"
        return True


class _FormateadorJSON(logging.Formatter):
    """Serializa los registros como una linea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "nivel": record.levelname,
            "mensaje": record.getMessage(),
            "correlacion": getattr(record, "correlacion", "-"),
            "logger": record.name,
        }
        extras = getattr(record, "campos", None)
        if isinstance(extras, dict):
            payload.update(extras)
        if record.exc_info:
            payload["error"] = redactar(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configurar_logging(nivel: str = "INFO") -> None:
    """Configura el logger raiz con formato JSON y filtro de correlacion."""
    raiz = logging.getLogger()
    raiz.setLevel(nivel.upper())
    for manejador in list(raiz.handlers):
        raiz.removeHandler(manejador)
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(_FormateadorJSON())
    manejador.addFilter(_FiltroCorrelacion())
    raiz.addHandler(manejador)


def obtener_logger(nombre: str) -> logging.Logger:
    """Devuelve un logger con los campos extra permitidos."""
    logger = logging.getLogger(nombre)
    logger.campos = {}  # type: ignore[attr-defined]
    return logger


def registrar_evento(
    logger: logging.Logger,
    nivel: int,
    mensaje: str,
    **campos: Any,
) -> None:
    """Emite un registro con campos estructurados, redactando valores sensibles."""
    seguros = {clave: redactar(str(valor)) for clave, valor in campos.items()}
    logger.log(nivel, mensaje, extra={"campos": seguros})


@contextmanager
def etapa(logger: logging.Logger, nombre: str, **campos: Any) -> Iterator[None]:
    """Mide y registra la duracion de una etapa de la consulta."""
    import time

    inicio = time.perf_counter()
    try:
        yield
    finally:
        duracion = round((time.perf_counter() - inicio) * 1000, 2)
        registrar_evento(
            logger,
            logging.INFO,
            f"etapa:{nombre}",
            duracion_ms=duracion,
            **campos,
        )


def es_campo_sensible(nombre: str) -> bool:
    """Indica si un nombre de campo puede contener un secreto."""
    normalizado = re.sub(r"[^a-z]", "", nombre.lower())
    return any(campo in normalizado for campo in _CAMPOS_SENSIBLES)
