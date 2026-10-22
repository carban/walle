"""Pruebas de contrato contra el proveedor real (OpenRouter).

Se ejecutan solo de forma explicita:

    uv run pytest -m integration

Si no hay `OPENROUTER_API_KEY` en el entorno, se omiten.
"""

from __future__ import annotations

import os

import pytest

from walle.config import Settings
from walle.main import crear_aplicacion

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.integration


@pytest.fixture
def cliente() -> object:
    configuracion = Settings()
    if not configuracion.openrouter_api_key:
        pytest.skip("se requiere OPENROUTER_API_KEY (en el entorno o en .env)")
    from fastapi.testclient import TestClient

    app = crear_aplicacion(configuracion)
    with TestClient(app) as cliente_http:
        yield cliente_http


def test_consulta_real_responde_con_fuente(cliente: object) -> None:
    respuesta = cliente.post(  # type: ignore[attr-defined]
        "/api/consultar",
        json={"pregunta": "¿Cuál es el monto máximo del Crédito Productivo Impulso?"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "Exitosa"
    assert "50.000.000" in cuerpo["respuesta"]
    assert cuerpo["fuentes"]


def test_consulta_real_fuera_del_corpus(cliente: object) -> None:
    respuesta = cliente.post(  # type: ignore[attr-defined]
        "/api/consultar", json={"pregunta": "¿Cuál es el clima en Marte?"}
    )

    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "Sin información suficiente"
    assert cuerpo["respuesta"] == "No tengo información suficiente para responder."
