"""API del historial de consultas.

El recurso se expone como `/api/consultas` (nombre del dominio, con paginacion) y
como `/api/historial` (alias sin paginacion), para que ambos clientes funcionen.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from walle.api.esquema import BorradoRespuesta, ConsultaHistorial, Fuente
from walle.persistencia.modelo import Consulta
from walle.persistencia.repositorio import RepositorioConsultas

router = APIRouter(prefix="/api", tags=["historial"])

MENSAJE_NO_ENCONTRADA = "La consulta no fue encontrada."

#: Tope de consultas que devuelve una pagina del historial.
LIMITE_MAXIMO = 200


def obtener_repositorio(request: Request) -> RepositorioConsultas:
    """Obtiene el repositorio de consultas de la aplicacion."""
    return request.app.state.repositorio  # type: ignore[no-any-return]


DependenciaRepositorio = Annotated[RepositorioConsultas, Depends(obtener_repositorio)]


def _a_historial(consulta: Consulta) -> ConsultaHistorial:
    """Convierte una consulta del repositorio en el esquema de la API."""
    return ConsultaHistorial(
        id=consulta.id or 0,
        pregunta=consulta.pregunta,
        fecha_hora=consulta.fecha_hora,
        respuesta=consulta.respuesta,
        fuentes=[
            Fuente(documento=fuente["documento"], fragmento=fuente["fragmento"])
            for fuente in consulta.fuentes
        ],
        estado=consulta.estado,
        duracion_ms=consulta.duracion_ms,
        modelo=consulta.modelo,
    )


@router.get(
    "/consultas",
    response_model=list[ConsultaHistorial],
    summary="Lista las consultas registradas (paginado)",
)
@router.get(
    "/historial",
    response_model=list[ConsultaHistorial],
    summary="Lista las consultas registradas",
    include_in_schema=False,
)
async def listar(
    repositorio: DependenciaRepositorio,
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAXIMO)] = 50,
    desplazamiento: Annotated[int, Query(ge=0)] = 0,
) -> list[ConsultaHistorial]:
    """Devuelve el historial, de la consulta mas reciente a la mas antigua."""
    consultas = repositorio.listar()
    return [
        _a_historial(consulta)
        for consulta in consultas[desplazamiento : desplazamiento + limite]
    ]


@router.get(
    "/consultas/{indice}",
    response_model=ConsultaHistorial,
    summary="Consulta una consulta por indice",
)
@router.get(
    "/historial/{indice}",
    response_model=ConsultaHistorial,
    summary="Consulta una consulta por indice (alias)",
    include_in_schema=False,
)
async def obtener(indice: int, repositorio: DependenciaRepositorio) -> ConsultaHistorial:
    """Devuelve la consulta indicada con sus fuentes estructuradas."""
    consulta = repositorio.obtener(indice)
    if consulta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MENSAJE_NO_ENCONTRADA)
    return _a_historial(consulta)


@router.delete(
    "/consultas/{indice}",
    response_model=BorradoRespuesta,
    summary="Borra una consulta por indice",
)
@router.delete(
    "/historial/{indice}",
    response_model=BorradoRespuesta,
    summary="Borra una consulta por indice (alias)",
    include_in_schema=False,
)
async def eliminar(indice: int, repositorio: DependenciaRepositorio) -> BorradoRespuesta:
    """Elimina la consulta indicada sin afectar al resto del historial."""
    if not repositorio.eliminar(indice):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MENSAJE_NO_ENCONTRADA)
    return BorradoRespuesta(eliminado=True, indice=indice)
