"""Rutas HTTP del asistente."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from walle.api.esquema import (
    ConsultaRequest,
    ConsultaResponse,
    CorpusInfo,
    DocumentoInfo,
    PersistenciaInfo,
    ProveedorInfo,
    SaludResponse,
)
from walle.dominio.consulta import Orquestador
from walle.dominio.estados import Estado
from walle.persistencia.repositorio import RepositorioSQLite
from walle.seguridad.trazas import obtener_correlacion

router = APIRouter(prefix="/api", tags=["walle"])
logger = logging.getLogger("walle.api")


def obtener_orquestador(request: Request) -> Orquestador:
    """Obtiene el orquestador construido en el ciclo de vida de la aplicacion."""
    return request.app.state.orquestador  # type: ignore[no-any-return]


DependenciaOrquestador = Annotated[Orquestador, Depends(obtener_orquestador)]


@router.post(
    "/consultar",
    response_model=ConsultaResponse,
    summary="Realiza una consulta al asistente",
)
async def consultar(
    cuerpo: ConsultaRequest,
    respuesta_http: Response,
    orquestador: DependenciaOrquestador,
) -> ConsultaResponse:
    """Responde una pregunta con base en la documentacion permitida."""
    resultado = orquestador.consultar(cuerpo.pregunta)
    respuesta_http.headers["X-Correlation-ID"] = obtener_correlacion() or "-"
    return ConsultaResponse(
        respuesta=resultado.respuesta,
        fuentes=resultado.fuentes,  # type: ignore[arg-type]
        estado=resultado.estado,
        consulta_id=resultado.consulta_id,
        duracion_ms=resultado.duracion_ms,
        modelo=resultado.modelo,
    )


@router.get("/documentos", response_model=list[DocumentoInfo], summary="Documentos del corpus")
async def documentos(orquestador: DependenciaOrquestador) -> list[DocumentoInfo]:
    """Lista los documentos disponibles para el asistente."""
    corpus = orquestador.corpus
    return [
        DocumentoInfo(nombre=documento.nombre, secciones=len(documento.secciones))
        for documento in corpus.documentos
    ]


@router.get("/salud", response_model=SaludResponse, summary="Estado de la aplicacion")
async def salud(request: Request, orquestador: DependenciaOrquestador) -> SaludResponse:
    """Informa el estado del corpus, del proveedor de modelo y de la persistencia."""
    from walle import __version__

    corpus = orquestador.corpus
    secciones = sum(len(documento.secciones) for documento in corpus.documentos)
    repositorio = request.app.state.repositorio
    return SaludResponse(
        estado="ok",
        version=__version__,
        corpus=CorpusInfo(
            documentos=len(corpus.documentos),
            secciones_totales=secciones,
            duplicados=len(corpus.duplicados),
            omitidos=len(corpus.documentos_omitidos),
        ),
        proveedor=ProveedorInfo(
            modelo=orquestador.modelo,
            disponible=orquestador.proveedor_disponible,
        ),
        persistencia=PersistenciaInfo(
            disponible=bool(request.app.state.persistencia_disponible),
            motor="sqlite" if isinstance(repositorio, RepositorioSQLite) else "memoria",
            ruta=str(getattr(repositorio, "ruta", "")),
        ),
        correlacion=obtener_correlacion() or "-",
    )


@router.get("/estados", response_model=list[str], summary="Estados validos")
async def estados() -> list[str]:
    """Lista los estados de respuesta admitidos por el sistema."""
    return [estado.value for estado in Estado]


__all__ = ["router", "status"]
