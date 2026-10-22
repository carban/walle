"""Pruebas del repositorio SQLite y del esquema."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from walle.dominio.estados import Estado
from walle.persistencia.esquema import (
    VERSION_ESQUEMA,
    inicializar_esquema,
    version_esquema,
)
from walle.persistencia.modelo import Consulta
from walle.persistencia.repositorio import (
    RepositorioEnMemoria,
    RepositorioSQLite,
    crear_repositorio,
)


def _consulta(pregunta: str = "pregunta", fecha: str = "2026-10-21T10:00:00+00:00") -> Consulta:
    return Consulta(
        id=None,
        pregunta=pregunta,
        fecha_hora=fecha,
        respuesta="respuesta",
        fuentes=[{"documento": "Productos de Crédito.md", "fragmento": "Condiciones"}],
        estado=Estado.EXITOSA,
        duracion_ms=1234,
        modelo="cohere/north-mini-code:free",
    )


@pytest.fixture
def repositorio(tmp_path: Path) -> RepositorioSQLite:
    return RepositorioSQLite(tmp_path / "walle.db")


def test_registrar_devuelve_indice(repositorio: RepositorioSQLite) -> None:
    indice = repositorio.registrar(_consulta())

    assert indice == 1
    assert repositorio.obtener(indice) is not None


def test_consulta_guarda_todos_los_campos(repositorio: RepositorioSQLite) -> None:
    indice = repositorio.registrar(_consulta())

    consulta = repositorio.obtener(indice)
    assert consulta is not None
    assert consulta.pregunta == "pregunta"
    assert consulta.respuesta == "respuesta"
    assert consulta.estado == Estado.EXITOSA
    assert consulta.duracion_ms == 1234
    assert consulta.modelo == "cohere/north-mini-code:free"
    assert consulta.fuentes == [
        {"documento": "Productos de Crédito.md", "fragmento": "Condiciones"}
    ]


def test_listar_ordenado_de_mas_reciente_a_mas_antigua(
    repositorio: RepositorioSQLite,
) -> None:
    repositorio.registrar(_consulta("primera", "2026-10-21T10:00:00+00:00"))
    repositorio.registrar(_consulta("segunda", "2026-10-22T10:00:00+00:00"))

    historial = repositorio.listar()

    assert [consulta.pregunta for consulta in historial] == ["segunda", "primera"]


def test_obtener_indice_inexistente_devuelve_none(repositorio: RepositorioSQLite) -> None:
    assert repositorio.obtener(9999) is None


def test_eliminar_por_indice(repositorio: RepositorioSQLite) -> None:
    repositorio.registrar(_consulta("primera"))
    indice = repositorio.registrar(_consulta("segunda"))

    assert repositorio.eliminar(indice) is True
    assert repositorio.eliminar(indice) is False
    assert len(repositorio.listar()) == 1


def test_eliminar_no_afecta_a_las_demas(repositorio: RepositorioSQLite) -> None:
    primero = repositorio.registrar(_consulta("primera"))
    segundo = repositorio.registrar(_consulta("segunda"))

    repositorio.eliminar(primero)

    assert repositorio.obtener(segundo) is not None


def test_el_esquema_es_idempotente(tmp_path: Path) -> None:
    ruta = tmp_path / "walle.db"

    RepositorioSQLite(ruta)
    repositorio = RepositorioSQLite(ruta)
    repositorio.registrar(_consulta())

    assert len(RepositorioSQLite(ruta).listar()) == 1


def test_la_version_del_esquema_queda_registrada(tmp_path: Path) -> None:
    ruta = tmp_path / "walle.db"
    RepositorioSQLite(ruta)

    conexion = sqlite3.connect(ruta)
    try:
        assert version_esquema(conexion) == VERSION_ESQUEMA
    finally:
        conexion.close()


def test_la_base_sobrevive_al_reinicio(tmp_path: Path) -> None:
    ruta = tmp_path / "walle.db"
    RepositorioSQLite(ruta).registrar(_consulta("persistente"))

    assert RepositorioSQLite(ruta).listar()[0].pregunta == "persistente"


def test_una_pregunta_con_sql_no_se_interpreta(repositorio: RepositorioSQLite) -> None:
    indice = repositorio.registrar(
        _consulta("'; DROP TABLE consultas; --")
    )

    assert repositorio.obtener(indice) is not None
    assert len(repositorio.listar()) == 1


def test_el_modo_degradado_usa_memoria(tmp_path: Path) -> None:
    # La ruta apunta a un archivo, no a un directorio: no se puede crear la base.
    bloqueo = tmp_path / "bloqueo"
    bloqueo.write_text("no soy un directorio", encoding="utf-8")

    repositorio, disponible = crear_repositorio(bloqueo / "walle.db")

    assert disponible is False
    assert isinstance(repositorio, RepositorioEnMemoria)
    assert repositorio.registrar(_consulta()) == 1


def test_escrituras_concurrentes_no_producen_bloqueos(tmp_path: Path) -> None:
    repositorio = RepositorioSQLite(tmp_path / "walle.db")
    errores: list[Exception] = []

    def escribir(indice: int) -> None:
        try:
            repositorio.registrar(_consulta(f"consulta {indice}"))
        except Exception as error:  # noqa: BLE001
            errores.append(error)

    hilos = [threading.Thread(target=escribir, args=(indice,)) for indice in range(10)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert errores == []
    assert len(repositorio.listar()) == 10


def test_el_esquema_se_crea_solo(tmp_path: Path) -> None:
    ruta = tmp_path / "walle.db"
    conexion = sqlite3.connect(ruta)
    try:
        inicializar_esquema(conexion)
        inicializar_esquema(conexion)
        tablas = {
            fila[0]
            for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conexion.close()

    assert "consultas" in tablas
