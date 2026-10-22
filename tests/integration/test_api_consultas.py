"""Pruebas de la API de historial: recurso /api/consultas y alias /api/historial."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.dobles import ClienteFalso
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
    app = crear_aplicacion(
        configuracion, cliente_modelo=ClienteFalso(["El monto máximo es $50.000.000."])
    )
    with TestClient(app) as cliente_http:
        yield cliente_http


def _consultar(cliente: TestClient, pregunta: str) -> dict[str, object]:
    respuesta = cliente.post("/api/consultar", json={"pregunta": pregunta})
    assert respuesta.status_code == 200
    return respuesta.json()


def test_consultas_devuelve_el_historial_paginado(cliente: TestClient) -> None:
    _consultar(cliente, "primera consulta")
    _consultar(cliente, "segunda consulta")

    respuesta = cliente.get("/api/consultas?limite=50&desplazamiento=0")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 2
    assert cuerpo[0]["pregunta"] == "segunda consulta"


def test_consultas_respeta_el_limite_y_el_desplazamiento(cliente: TestClient) -> None:
    for indice in range(5):
        _consultar(cliente, f"consulta {indice}")

    pagina = cliente.get("/api/consultas?limite=2&desplazamiento=0").json()
    siguiente = cliente.get("/api/consultas?limite=2&desplazamiento=2").json()

    assert len(pagina) == 2
    assert len(siguiente) == 2
    assert pagina[0]["pregunta"] != siguiente[0]["pregunta"]


def test_historial_sigue_funcionando_como_alias(cliente: TestClient) -> None:
    _consultar(cliente, "una consulta")

    assert len(cliente.get("/api/historial").json()) == 1


def test_consulta_por_indice_en_consultas(cliente: TestClient) -> None:
    cuerpo = _consultar(cliente, "¿Cuál es el monto máximo del Crédito Productivo Impulso?")

    respuesta = cliente.get(f"/api/consultas/{cuerpo['consulta_id']}")

    assert respuesta.status_code == 200
    assert respuesta.json()["respuesta"] == cuerpo["respuesta"]


def test_borrado_por_indice_en_consultas(cliente: TestClient) -> None:
    cuerpo = _consultar(cliente, "una consulta")

    respuesta = cliente.delete(f"/api/consultas/{cuerpo['consulta_id']}")

    assert respuesta.status_code == 200
    assert cliente.get("/api/consultas").json() == []


def test_indice_inexistente_devuelve_404(cliente: TestClient) -> None:
    assert cliente.get("/api/consultas/9999").status_code == 404
    assert cliente.delete("/api/consultas/9999").status_code == 404


def test_los_parametros_invalidos_se_rechazan(cliente: TestClient) -> None:
    assert cliente.get("/api/consultas?limite=0").status_code == 422
    assert cliente.get("/api/consultas?limite=9999").status_code == 422
    assert cliente.get("/api/consultas?desplazamiento=-1").status_code == 422
