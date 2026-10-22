"""Persistencia de las consultas realizadas al asistente.

La aplicacion depende del protocolo `RepositorioConsultas`, nunca de SQLite: asi la
base puede reemplazarse y las pruebas no necesitan disco. La implementacion real usa
un archivo SQLite en `storage/`, con una conexion por hilo.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from walle.persistencia.esquema import configurar_conexion, inicializar_esquema
from walle.persistencia.modelo import Consulta

logger = logging.getLogger("walle.persistencia")

__all__ = [
    "Consulta",
    "RepositorioConsultas",
    "RepositorioEnMemoria",
    "RepositorioSQLite",
    "crear_repositorio",
    "ahora_iso",
]


def ahora_iso() -> str:
    """Momento actual en ISO-8601 UTC."""
    return datetime.now(UTC).isoformat()


class RepositorioConsultas(Protocol):
    """Contrato de persistencia que consume la aplicacion."""

    def registrar(self, consulta: Consulta) -> int:
        """Guarda la consulta y devuelve el indice asignado."""
        ...

    def listar(self) -> list[Consulta]:
        """Devuelve todas las consultas, de la mas reciente a la mas antigua."""
        ...

    def obtener(self, indice: int) -> Consulta | None:
        """Devuelve la consulta con ese indice, o None si no existe."""
        ...

    def eliminar(self, indice: int) -> bool:
        """Elimina la consulta con ese indice; indica si existia."""
        ...


@dataclass
class RepositorioEnMemoria:
    """Implementacion en memoria: doble de pruebas y modo degradado."""

    consultas: list[Consulta] = field(default_factory=list)
    _siguiente: int = 1

    def registrar(self, consulta: Consulta) -> int:
        """Guarda la consulta con el siguiente indice disponible."""
        indice = self._siguiente
        self._siguiente += 1
        self.consultas.append(
            Consulta(
                id=indice,
                pregunta=consulta.pregunta,
                fecha_hora=consulta.fecha_hora or ahora_iso(),
                respuesta=consulta.respuesta,
                fuentes=list(consulta.fuentes),
                estado=consulta.estado,
                duracion_ms=consulta.duracion_ms,
                modelo=consulta.modelo,
            )
        )
        return indice

    def listar(self) -> list[Consulta]:
        """Devuelve las consultas de la mas reciente a la mas antigua."""
        return sorted(
            self.consultas,
            key=lambda consulta: (consulta.fecha_hora, consulta.id or 0),
            reverse=True,
        )

    def obtener(self, indice: int) -> Consulta | None:
        """Devuelve la consulta con ese indice, o None si no existe."""
        return next((consulta for consulta in self.consultas if consulta.id == indice), None)

    def eliminar(self, indice: int) -> bool:
        """Elimina la consulta con ese indice; indica si existia."""
        for posicion, consulta in enumerate(self.consultas):
            if consulta.id == indice:
                del self.consultas[posicion]
                return True
        return False


class RepositorioSQLite:
    """Repositorio sobre un archivo SQLite local."""

    def __init__(self, ruta: Path) -> None:
        self._ruta = Path(ruta)
        self._local = threading.local()
        if str(self._ruta) != ":memory:":
            self._ruta.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    @property
    def ruta(self) -> Path:
        """Ruta del archivo de base de datos."""
        return self._ruta

    def _conexion(self) -> sqlite3.Connection:
        """Devuelve la conexion del hilo actual, creandola si hace falta."""
        conexion: sqlite3.Connection | None = getattr(self._local, "conexion", None)
        if conexion is None:
            conexion = sqlite3.connect(
                self._ruta, timeout=5.0, check_same_thread=False, isolation_level="DEFERRED"
            )
            conexion.row_factory = sqlite3.Row
            configurar_conexion(conexion)
            self._local.conexion = conexion
        return conexion

    def _inicializar(self) -> None:
        """Crea el esquema de forma idempotente."""
        inicializar_esquema(self._conexion())

    def registrar(self, consulta: Consulta) -> int:
        """Guarda la consulta en una transaccion y devuelve el indice asignado."""
        conexion = self._conexion()
        with conexion:
            cursor = conexion.execute(
                """
                INSERT INTO consultas
                    (pregunta, fecha_hora, respuesta, fuentes, estado, duracion_ms, modelo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                consulta.fila,
            )
            return int(cursor.lastrowid or 0)

    def listar(self) -> list[Consulta]:
        """Devuelve todas las consultas, de la mas reciente a la mas antigua."""
        filas = self._conexion().execute(
            "SELECT * FROM consultas ORDER BY fecha_hora DESC, id DESC"
        ).fetchall()
        return [Consulta.desde_fila(fila) for fila in filas]

    def obtener(self, indice: int) -> Consulta | None:
        """Devuelve la consulta con ese indice, o None si no existe."""
        fila = self._conexion().execute(
            "SELECT * FROM consultas WHERE id = ?", (indice,)
        ).fetchone()
        return Consulta.desde_fila(fila) if fila else None

    def eliminar(self, indice: int) -> bool:
        """Elimina la consulta con ese indice; indica si existia."""
        conexion = self._conexion()
        with conexion:
            cursor = conexion.execute("DELETE FROM consultas WHERE id = ?", (indice,))
            return cursor.rowcount > 0

    def cerrar(self) -> None:
        """Cierra la conexion del hilo actual."""
        conexion: sqlite3.Connection | None = getattr(self._local, "conexion", None)
        if conexion is not None:
            conexion.close()
            self._local.conexion = None


def crear_repositorio(ruta: Path) -> tuple[RepositorioConsultas, bool]:
    """Crea el repositorio sobre SQLite y degrada a memoria si la base no abre.

    Devuelve el repositorio y un indicador de disponibilidad de la persistencia.
    """
    try:
        return RepositorioSQLite(ruta), True
    except (sqlite3.Error, OSError) as error:
        logger.error(
            "persistencia_no_disponible tipo=%s mensaje=%s",
            type(error).__name__,
            str(error)[:200],
        )
        return RepositorioEnMemoria(), False
