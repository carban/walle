"""Pruebas de la configuracion y de la respuesta extractiva de respaldo."""

from __future__ import annotations

from pathlib import Path

from walle.config import DOCUMENTOS_EXCLUIDOS, DOCUMENTOS_PERMITIDOS, Settings
from walle.fallback.extractivo import responder_extrayendo
from walle.recuperacion.corpus import cargar_corpus

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "Data"


def test_valores_por_defecto() -> None:
    configuracion = Settings(_env_file=None, openrouter_api_key=None)

    assert configuracion.walle_modelo == "cohere/north-mini-code:free"
    assert configuracion.walle_umbral_relevancia == 1.0
    assert configuracion.hay_credencial_proveedor is False


def test_credencial_api_key2_es_valida() -> None:
    """OPENROUTER_API_KEY2 es reconocida como credencial valida del proveedor."""
    configuracion = Settings(
        _env_file=None,
        openrouter_api_key=None,
        openrouter_api_key2="sk-or-v1-prueba123",
    )

    assert configuracion.hay_credencial_proveedor is True
    assert configuracion.openrouter_api_key2 == "sk-or-v1-prueba123"


def test_origenes_permitidos_por_defecto() -> None:
    configuracion = Settings(_env_file=None)

    assert "http://localhost:5173" in configuracion.origins_permitidos
    assert "http://127.0.0.1:5173" in configuracion.origins_permitidos


def test_documento_restringido_esta_excluido() -> None:
    assert "Información restringida.md" in DOCUMENTOS_EXCLUIDOS
    assert "Información restringida.md" not in DOCUMENTOS_PERMITIDOS


def test_fallback_extrae_el_dato_relevante() -> None:
    corpus = cargar_corpus(directorio=DATA, permitidos=("Productos de Crédito.md",))

    texto, fuentes = responder_extrayendo(
        list(corpus.documentos), "¿Cuál es el monto máximo del Crédito Productivo Impulso?"
    )

    assert "50.000.000" in texto
    assert fuentes[0]["documento"] == "Productos de Crédito.md"


def test_fallback_sin_coincidencia_devuelve_mensaje_canonico() -> None:
    corpus = cargar_corpus(directorio=DATA, permitidos=("Productos de Crédito.md",))

    texto, fuentes = responder_extrayendo(list(corpus.documentos), "xyzzy")

    assert texto == "No tengo información suficiente para responder."
    assert fuentes == []
