"""API del historial de consultas."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from walle.api.esquema import BorradoRespuesta, ConsultaHistorial
from walle.persistencia.repositorio import RepositorioConsultas

router = APIRouter(prefix="/api/historial", tags=["historial"])

MENSAJE_NO_ENCONTRADA = "La consulta no fue encontrada."


def obtener_repositorio(request: Request) -> RepositorioConsultas:
    """Obtiene el repositorio de consultas de la aplicacion."""
    return request.app.state.repositorio  # type: ignore[no-any-return]


DependenciaRepositorio = Annotated[RepositorioConsultas, Depends(obtener_repositorio)]


@router.get("", response_model=list[ConsultaHistorial], summary="Lista todas las consultas")
async def listar(repositorio: DependenciaRepositorio) -> list[ConsultaHistorial]:
    """Devuelve el historial completo, de la consulta mas reciente a la mas antigua."""
    return [
        ConsultaHistorial(
            id=consulta.id or 0,
            pregunta=consulta.pregunta,
            fecha_hora=consulta.fecha_hora,
            respuesta=consulta.respuesta,
            fuentes=consulta.fuentes,  # type: ignore[arg-type]
            estado=consulta.estado,
            duracion_ms=consulta.duracion_ms,
            modelo=consulta.modelo,
        )
        for consulta in repositorio.listar()
    ]


@router.get(
    "/{indice}", response_model=ConsultaHistorial, summary="Consulta una consulta por indice"
)
async def obtener(indice: int, repositorio: DependenciaRepositorio) -> ConsultaHistorial:
    """Devuelve la consulta indicada con sus fuentes estructuradas."""
    consulta = repositorio.obtener(indice)
    if consulta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MENSAJE_NO_ENCONTRADA)
    return ConsultaHistorial(
        id=consulta.id or 0,
        pregunta=consulta.pregunta,
        fecha_hora=consulta.fecha_hora,
        respuesta=consulta.respuesta,
        fuentes=consulta.fuentes,  # type: ignore[arg-type]
        estado=consulta.estado,
        duracion_ms=consulta.duracion_ms,
        modelo=consulta.modelo,
    )


@router.delete(
    "/{indice}", response_model=BorradoRespuesta, summary="Borra una consulta por indice"
)
async def eliminar(indice: int, repositorio: DependenciaRepositorio) -> BorradoRespuesta:
    """Elimina la consulta indicada sin afectar al resto del historial."""
    if not repositorio.eliminar(indice):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MENSAJE_NO_ENCONTRADA)
    return BorradoRespuesta(eliminado=True, indice=indice)
