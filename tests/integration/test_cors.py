"""Pruebas de la configuracion CORS de la API.

En desarrollo el frontend corre en otro puerto (5173) que la API (8000): sin una
allowlist explicita, el navegador bloquea las peticiones.
"""

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


@pytest.mark.parametrize(
    "origen",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
def test_se_permite_el_origen_de_desarrollo(cliente: TestClient, origen: str) -> None:
    respuesta = cliente.options(
        "/api/consultar",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == origen


def test_no_se_permite_un_origen_desconocido(cliente: TestClient) -> None:
    respuesta = cliente.options(
        "/api/consultar",
        headers={
            "Origin": "https://sitio-malicioso.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in respuesta.headers


def test_la_respuesta_incluye_la_cabecera_de_origen(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/salud", headers={"Origin": "http://localhost:5173"})

    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_no_se_admite_el_comodin_origen(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/salud", headers={"Origin": "https://cualquiera.example"})

    assert respuesta.headers.get("access-control-allow-origin") != "*"
