"""Pruebas de la separacion entre la API y el frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from walle.config import Settings
from walle.main import crear_aplicacion

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "Data"


def _configuracion(tmp_path: Path, **extra: object) -> Settings:
    return Settings(
        _env_file=None,
        openrouter_api_key=None,
        walle_data_dir=DATA,
        walle_db_path=tmp_path / "walle.db",
        walle_log_level="WARNING",
        **extra,  # type: ignore[arg-type]
    )


def test_la_raiz_identifica_a_la_api(tmp_path: Path) -> None:
    with TestClient(crear_aplicacion(_configuracion(tmp_path))) as cliente:
        respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["servicio"] == "walle-api"
    assert cuerpo["consultar"] == "/api/consultar"
    assert cuerpo["frontend"] == "http://localhost:5173"


def test_la_api_no_sirve_el_frontend_por_defecto(tmp_path: Path) -> None:
    with TestClient(crear_aplicacion(_configuracion(tmp_path))) as cliente:
        respuesta = cliente.get("/cualquier-ruta")

    assert respuesta.status_code == 404
    assert "text/html" not in respuesta.headers.get("content-type", "")


def test_el_modo_de_un_solo_servicio_es_opt_in(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Walle</title>", encoding="utf-8")

    configuracion = _configuracion(tmp_path, walle_servir_frontend=True, walle_frontend_dir=dist)

    with TestClient(crear_aplicacion(configuracion)) as cliente:
        respuesta = cliente.get("/cualquier-ruta")

    assert respuesta.status_code == 200
    assert "Walle" in respuesta.text


def test_las_rutas_de_api_siguen_siendo_de_la_api(tmp_path: Path) -> None:
    with TestClient(crear_aplicacion(_configuracion(tmp_path))) as cliente:
        respuesta = cliente.get("/api/ruta-inexistente")

    assert respuesta.status_code == 404
    assert respuesta.headers.get("content-type", "").startswith("application/json")
