"""Fabrica de la aplicacion FastAPI.

Aqui se conectan las piezas: corpus, proveedor de modelo, repositorio y orquestador.
El contrato de la API no depende de ninguna de ellas.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from walle import __version__
from walle.api.historial import router as router_historial
from walle.api.rutas import router
from walle.config import (
    DOCUMENTOS_EXCLUIDOS,
    DOCUMENTOS_PERMITIDOS,
    Settings,
    obtener_configuracion,
)
from walle.dominio.consulta import Orquestador
from walle.modelo.cliente import ClienteOpenRouter
from walle.persistencia.repositorio import (
    RepositorioConsultas,
    crear_repositorio,
)
from walle.recuperacion.corpus import cargar_corpus
from walle.seguridad.trazas import (
    configurar_logging,
    correlacion,
    nueva_correlacion,
    obtener_correlacion,
    registrar_evento,
)

logger = logging.getLogger("walle")


def construir_orquestador(
    settings: Settings,
    repositorio: RepositorioConsultas,
    cliente_modelo: object | None = None,
) -> Orquestador:
    """Construye el orquestador con el corpus, el proveedor y el repositorio dados.

    `cliente_modelo` permite inyectar un doble en las pruebas; si es None se construye
    el cliente real de OpenRouter cuando hay credencial.
    """
    corpus = cargar_corpus(
        directorio=settings.walle_data_dir,
        permitidos=DOCUMENTOS_PERMITIDOS,
        excluidos=DOCUMENTOS_EXCLUIDOS,
    )
    logger.info(
        "corpus_cargado documentos=%d duplicados=%d omitidos=%d",
        len(corpus.documentos),
        len(corpus.duplicados),
        len(corpus.documentos_omitidos),
    )

    cliente = cliente_modelo
    if cliente is None and settings.hay_credencial_proveedor and settings.openrouter_api_key:
        cliente = ClienteOpenRouter(
            api_key=settings.openrouter_api_key,
            modelo=settings.walle_modelo,
            timeout=settings.walle_timeout_segundos,
            reintentos=settings.walle_reintentos,
        )
    elif cliente is None:
        logger.warning("sin_credencial_proveedor modo=degradado")

    return Orquestador(
        corpus=corpus,
        cliente_modelo=cliente,  # type: ignore[arg-type]
        repositorio=repositorio,
        umbral_relevancia=settings.walle_umbral_relevancia,
    )


def crear_aplicacion(
    settings: Settings | None = None,
    cliente_modelo: object | None = None,
) -> FastAPI:
    """Crea la instancia de FastAPI con sus dependencias ya conectadas."""
    configuracion = settings or obtener_configuracion()
    configurar_logging(configuracion.walle_log_level)

    @asynccontextmanager
    async def ciclo_vida(app: FastAPI) -> AsyncIterator[None]:
        repositorio, disponible = crear_repositorio(configuracion.walle_db_path)
        app.state.repositorio = repositorio
        app.state.persistencia_disponible = disponible
        app.state.orquestador = construir_orquestador(configuracion, repositorio, cliente_modelo)
        yield

    app = FastAPI(
        title="Walle - Asistente de asesores comerciales",
        version=__version__,
        description=(
            "API interna que responde consultas sobre creditos, microseguros, "
            "procedimientos y politicas internas, fundamentadas en la documentacion de Data/."
        ),
        lifespan=ciclo_vida,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuracion.origins_permitidos,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID"],
    )

    @app.middleware("http")
    async def identificador_correlacion(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Asigna un identificador de correlacion a cada peticion."""
        with correlacion(nueva_correlacion()) as identificador:
            respuesta = await call_next(request)
            respuesta.headers["X-Correlation-ID"] = identificador
            return respuesta

    @app.exception_handler(Exception)
    async def manejar_error_inesperado(request: Request, error: Exception) -> JSONResponse:
        """Responde con un error generico, sin filtrar detalles internos."""
        registrar_evento(
            logger,
            logging.ERROR,
            "error_no_controlado",
            ruta=request.url.path,
            tipo=type(error).__name__,
            correlacion=obtener_correlacion() or "-",
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Ocurrió un error interno. Inténtalo de nuevo.",
                "correlacion": obtener_correlacion() or "-",
            },
        )

    @app.get("/", tags=["walle"], summary="Identificacion del servicio")
    async def raiz() -> dict[str, str]:
        """Identifica el servicio y señala los puntos de entrada principales."""
        from walle import __version__

        return {
            "servicio": "walle-api",
            "version": __version__,
            "descripcion": "API del asistente Walle para asesores comerciales.",
            "consultar": "/api/consultar",
            "historial": "/api/historial",
            "salud": "/api/salud",
            "documentacion": "/docs",
            "frontend": "http://localhost:5173",
        }

    app.include_router(router)
    app.include_router(router_historial)

    _montar_frontend(app, configuracion)
    return app


def _montar_frontend(app: FastAPI, settings: Settings) -> None:
    """Sirve la compilacion del frontend, solo si se pide explicitamente.

    Por defecto la API y el frontend son servicios separados: el puerto 8000 expone
    la API y el 5173 el chat. El modo de un solo servicio es opt-in.
    """
    if not settings.walle_servir_frontend:
        return

    directorio = settings.walle_frontend_dir
    if not directorio.is_dir():
        logger.warning("frontend_no_encontrado ruta=%s", directorio)
        return

    if (directorio / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=directorio / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    async def aplicacion(ruta: str) -> FileResponse:
        """Sirve el index del frontend para cualquier ruta del cliente."""
        if ruta.startswith("api"):
            # Las rutas de la API que no existen deben seguir siendo 404.
            raise HTTPException(status_code=404, detail="Recurso no encontrado.")
        return FileResponse(directorio / "index.html")


app = crear_aplicacion()


def main() -> None:
    """Punto de entrada para `uv run walle`."""
    import uvicorn

    uvicorn.run("walle.main:app", host="127.0.0.1", port=8000, reload=False)
