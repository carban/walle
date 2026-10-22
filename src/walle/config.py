"""Configuracion de la aplicacion, leida del entorno y del archivo .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

#: Documentos que el asistente puede consultar. La lista es una allowlist explicita:
#: cualquier archivo de Data/ que no aparezca aqui queda fuera del sistema.
DOCUMENTOS_PERMITIDOS: tuple[str, ...] = (
    "Manual del Asesor Comercial.md",
    "Políticas de Atención.md",
    "Portafolio de Microseguros.md",
    "Procedimientos Operativos.md",
    "Productos de Crédito.md",
)

#: Documentos excluidos de forma expresa. No se cargan, no se citan y no se persisten.
DOCUMENTOS_EXCLUIDOS: tuple[str, ...] = ("Información restringida.md",)


class Settings(BaseSettings):
    """Parametros de ejecucion.

    Todos los valores tienen un default seguro: sin credenciales el sistema opera
    en modo degradado (respuesta extractiva local) y sin exponer nada.
    """

    model_config = SettingsConfigDict(
        env_file=RAIZ_PROYECTO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")

    walle_modelo: str = "minimax/minimax-m3.1-flash:free"
    walle_timeout_segundos: float = 30.0
    walle_reintentos: int = 1
    walle_umbral_relevancia: float = 1.0
    walle_data_dir: Path = RAIZ_PROYECTO / "Data"
    walle_db_path: Path = RAIZ_PROYECTO / "storage" / "walle.db"
    walle_log_level: str = "INFO"
    walle_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    walle_servir_frontend: bool = False
    walle_frontend_dir: Path = RAIZ_PROYECTO / "frontend" / "dist"

    @property
    def origins_permitidos(self) -> list[str]:
        """Origenes CORS permitidos, en texto separado por comas."""
        return [origen.strip() for origen in self.walle_cors_origins.split(",") if origen.strip()]

    @property
    def hay_credencial_proveedor(self) -> bool:
        """Indica si hay clave de OpenRouter disponible."""
        return bool(self.openrouter_api_key)


@lru_cache(maxsize=1)
def obtener_configuracion() -> Settings:
    """Devuelve la configuracion cacheada del proceso."""
    return Settings()
