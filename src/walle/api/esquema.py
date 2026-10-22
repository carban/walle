"""Contratos HTTP de la API."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from walle.dominio.estados import Estado

Pregunta = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=2000,
        pattern=r"^[^\x00-\x08\x0b\x0c\x0e-\x1f]+$",
    ),
]


class ConsultaRequest(BaseModel):
    """Cuerpo de la peticion de consulta."""

    pregunta: Pregunta = Field(
        ...,
        description="Pregunta en lenguaje natural sobre la documentacion del asistente.",
        examples=["¿Cuál es el monto máximo del Crédito Productivo Impulso?"],
    )


class Fuente(BaseModel):
    """Documento y fragmento que sustentan una respuesta."""

    documento: str = Field(..., description="Nombre del documento del corpus.")
    fragmento: str = Field(..., description="Seccion del documento que sustenta la respuesta.")


class ConsultaResponse(BaseModel):
    """Respuesta de una consulta."""

    respuesta: str = Field(..., description="Texto generado con base en la documentacion.")
    fuentes: list[Fuente] = Field(default_factory=list, description="Fuentes citadas.")
    estado: Estado = Field(..., description="Estado de la respuesta.")
    consulta_id: int | None = Field(default=None, description="Indice de la consulta registrada.")
    duracion_ms: int = Field(
        default=0, description="Duracion total de la consulta en milisegundos."
    )
    modelo: str = Field(
        default="", description="Modelo utilizado, vacio si no se invoco al proveedor."
    )


class DocumentoInfo(BaseModel):
    """Documento disponible en el corpus."""

    nombre: str
    secciones: int


class CorpusInfo(BaseModel):
    """Estado del corpus documental."""

    documentos: int
    secciones_totales: int
    duplicados: int
    omitidos: int


class ProveedorInfo(BaseModel):
    """Estado del proveedor de modelo."""

    modelo: str
    disponible: bool


class SaludResponse(BaseModel):
    """Estado de salud de la aplicacion."""

    estado: str
    version: str
    corpus: CorpusInfo
    proveedor: ProveedorInfo
    correlacion: str
