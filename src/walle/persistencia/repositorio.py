"""Persistencia de las consultas realizadas al asistente.

La aplicacion depende del protocolo `RepositorioConsultas`, nunca de SQLite: asi la
base puede reemplazarse (caracteristica 002) y las pruebas no necesitan disco.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from walle.dominio.estados import Estado


def ahora_iso() -> str:
    """Momento actual en ISO-8601 UTC."""
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Consulta:
    """Una consulta registrada, con su respuesta y sus fuentes."""

    id: int | None
    pregunta: str
    fecha_hora: str
    respuesta: str
    fuentes: list[dict[str, str]]
    estado: Estado
    duracion_ms: int
    modelo: str = ""


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
        return sorted(self.consultas, key=lambda consulta: consulta.fecha_hora, reverse=True)

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
