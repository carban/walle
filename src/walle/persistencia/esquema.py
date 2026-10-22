"""Esquema de la base y apertura de conexiones.

La base es un archivo SQLite local: no hay servidor, ni dependencias externas, ni
configuracion que mantener. El esquema se crea de forma idempotente y se versiona con
`PRAGMA user_version` para que una evolucion futura sepa desde que version migrar.
"""

from __future__ import annotations

import sqlite3

VERSION_ESQUEMA = 1

DDL_TABLA = """
CREATE TABLE IF NOT EXISTS consultas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta    TEXT    NOT NULL,
    fecha_hora  TEXT    NOT NULL,
    respuesta   TEXT    NOT NULL,
    fuentes     TEXT    NOT NULL,
    estado      TEXT    NOT NULL,
    duracion_ms INTEGER NOT NULL,
    modelo      TEXT    NOT NULL DEFAULT ''
)
"""

DDL_INDICE = """
CREATE INDEX IF NOT EXISTS ix_consultas_fecha_hora ON consultas (fecha_hora DESC)
"""


def configurar_conexion(conexion: sqlite3.Connection) -> None:
    """Ajusta la conexion para durabilidad, concurrencia y rendimiento.

    WAL permite lecturas concurrentes mientras se escribe; `busy_timeout` hace que una
    escritura espere en lugar de fallar de inmediato si otra conexion esta escribiendo.
    """
    conexion.execute("PRAGMA journal_mode = WAL")
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.execute("PRAGMA synchronous = NORMAL")
    conexion.execute("PRAGMA busy_timeout = 5000")


def inicializar_esquema(conexion: sqlite3.Connection) -> None:
    """Crea el esquema si no existe y registra la version del esquema."""
    with conexion:
        conexion.execute(DDL_TABLA)
        conexion.execute(DDL_INDICE)
        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")


def version_esquema(conexion: sqlite3.Connection) -> int:
    """Version del esquema almacenada en la base."""
    fila = conexion.execute("PRAGMA user_version").fetchone()
    return int(fila[0]) if fila else 0
