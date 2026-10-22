"""Pruebas de la sonda de salud y de las cabeceras de la API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from walle.config import Settings
from walle.main import crear_aplicacion

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "Data"


@pytest.fixture
def cliente(tmp_path: Path) -> TestClient:
    configuracion = Settings(
        _env_file=None,
        openrouter_api_key=None,
        walle_data_dir=DATA,
        walle_db_path=tmp_path / "walle.db",
        walle_log_level="WARNING",
    )
    with TestClient(crear_aplicacion(configuracion)) as cliente_http:
        yield cliente_http


def test_la_sonda_health_responde_ok(cliente: TestClient) -> None:
    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["servicio"] == "walle-api"


def test_la_raiz_identifica_la_api(cliente: TestClient) -> None:
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert respuesta.json()["servicio"] == "walle-api"


def test_las_respuestas_de_la_api_no_se_cachean(cliente: TestClient) -> None:
    # Sin esto, el navegador puede guardar un fallo antiguo del proxy y seguir
    # mostrando el panel vacio aunque la API ya funcione.
    respuesta = cliente.get("/api/historial")

    assert respuesta.headers["cache-control"] == "no-store, no-cache, must-revalidate"
    assert respuesta.headers["pragma"] == "no-cache"
