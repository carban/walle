"""Pruebas de la construccion de fuentes y del repositorio en memoria."""

from __future__ import annotations

from pathlib import Path

from walle.dominio.estados import Estado
from walle.persistencia.repositorio import Consulta, RepositorioEnMemoria
from walle.recuperacion.corpus import cargar_corpus
from walle.recuperacion.fuentes import construir_fuentes
from walle.recuperacion.relevance import seleccionar_documentos

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "Data"


def test_fuentes_incluyen_documento_y_fragmento() -> None:
    corpus = cargar_corpus(directorio=DATA, permitidos=("Productos de Crédito.md",))
    seleccion = seleccionar_documentos(
        corpus, "¿Cuál es el monto máximo del Crédito Productivo Impulso?"
    )

    fuentes = construir_fuentes(seleccion)

    assert fuentes
    assert fuentes[0]["documento"] == "Productos de Crédito.md"
    assert fuentes[0]["fragmento"]


def test_fuentes_no_se_duplican() -> None:
    corpus = cargar_corpus(directorio=DATA, permitidos=("Productos de Crédito.md",))
    seleccion = seleccionar_documentos(
        corpus, "¿Cuál es el monto máximo del Crédito Productivo Impulso?"
    )

    fuentes = construir_fuentes(seleccion)
    documentos = [fuente["documento"] for fuente in fuentes]

    assert len(documentos) == len(set(documentos))


def _consulta(indice: int | None = None, pregunta: str = "pregunta") -> Consulta:
    return Consulta(
        id=indice,
        pregunta=pregunta,
        fecha_hora="2026-10-21T10:00:00+00:00",
        respuesta="respuesta",
        fuentes=[{"documento": "a.md", "fragmento": "b"}],
        estado=Estado.EXITOSA,
        duracion_ms=10,
        modelo="modelo",
    )


def test_repositorio_registra_y_asigna_indice() -> None:
    repositorio = RepositorioEnMemoria()

    indice = repositorio.registrar(_consulta())

    assert indice == 1
    assert repositorio.obtener(1) is not None


def test_repositorio_lista_de_mas_reciente_a_mas_antigua() -> None:
    repositorio = RepositorioEnMemoria()
    repositorio.registrar(_consulta())
    reciente = Consulta(
        id=None,
        pregunta="segunda",
        fecha_hora="2026-10-22T10:00:00+00:00",
        respuesta="r",
        fuentes=[],
        estado=Estado.EXITOSA,
        duracion_ms=1,
    )
    repositorio.registrar(reciente)

    historial = repositorio.listar()

    assert [consulta.pregunta for consulta in historial] == ["segunda", "pregunta"]


def test_repositorio_elimina_por_indice() -> None:
    repositorio = RepositorioEnMemoria()
    repositorio.registrar(_consulta())
    repositorio.registrar(_consulta())

    assert repositorio.eliminar(1) is True
    assert repositorio.eliminar(1) is False
    assert len(repositorio.listar()) == 1


def test_repositorio_devuelve_none_para_indice_inexistente() -> None:
    repositorio = RepositorioEnMemoria()

    assert repositorio.obtener(99) is None
