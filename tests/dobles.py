"""Dobles de prueba compartidos."""

from __future__ import annotations

from collections.abc import Sequence

from walle.modelo.cliente import ErrorProveedor
from walle.recuperacion.corpus import Documento


class ClienteFalso:
    """Cliente de modelo programable: devuelve respuestas o errores predefinidos."""

    def __init__(
        self,
        respuestas: Sequence[str] | None = None,
        error: Exception | None = None,
        modelo: str = "cohere/north-mini-code:free",
    ) -> None:
        self.respuestas = list(respuestas or [])
        self.error = error
        self.modelo = modelo
        self.invocaciones: list[tuple[str, tuple[str, ...]]] = []

    def responder(self, documentos: Sequence[Documento], pregunta: str) -> str:
        """Devuelve la respuesta programada o lanza el error configurado."""
        self.invocaciones.append((pregunta, tuple(documento.nombre for documento in documentos)))
        if self.error is not None:
            raise self.error
        if self.respuestas:
            return self.respuestas.pop(0)
        return "Respuesta de prueba."


class ClienteCaido:
    """Cliente que siempre falla, para probar la degradacion."""

    modelo = "cohere/north-mini-code:free"

    def __init__(self) -> None:
        self.invocaciones = 0

    def responder(self, documentos: Sequence[Documento], pregunta: str) -> str:
        """Simula un proveedor no disponible."""
        self.invocaciones += 1
        raise ErrorProveedor("proveedor no disponible")
