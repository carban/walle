"""Modelo de datos de la consulta persistida."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from walle.dominio.estados import Estado


@dataclass(frozen=True)
class Consulta:
    """Una consulta registrada, con su respuesta y sus fuentes."""

    id: int | None
    pregunta: str
    fecha_hora: str
    respuesta: str
    fuentes: list[dict[str, str]] = field(default_factory=list)
    estado: Estado = Estado.EXITOSA
    duracion_ms: int = 0
    modelo: str = ""

    @property
    def fila(self) -> tuple[object, ...]:
        """Valores de la consulta en el orden de las columnas de la tabla."""
        return (
            self.pregunta,
            self.fecha_hora,
            self.respuesta,
            json.dumps(self.fuentes, ensure_ascii=False),
            self.estado.value,
            self.duracion_ms,
            self.modelo,
        )

    @classmethod
    def desde_fila(cls, fila: sqlite3.Row) -> Consulta:
        """Construye una consulta a partir de una fila de SQLite."""
        try:
            fuentes = json.loads(fila["fuentes"])
        except (json.JSONDecodeError, TypeError):
            fuentes = []
        return cls(
            id=int(fila["id"]),
            pregunta=str(fila["pregunta"]),
            fecha_hora=str(fila["fecha_hora"]),
            respuesta=str(fila["respuesta"]),
            fuentes=list(fuentes),
            estado=Estado(fila["estado"]),
            duracion_ms=int(fila["duracion_ms"]),
            modelo=str(fila["modelo"] or ""),
        )
