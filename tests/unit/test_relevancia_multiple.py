"""Pruebas de la seleccion multiple de documentos."""

from __future__ import annotations

from pathlib import Path

from walle.recuperacion.corpus import cargar_corpus
from walle.recuperacion.relevance import seleccionar_documentos

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "Data"
PERMITIDOS = (
    "Manual del Asesor Comercial.md",
    "Políticas de Atención.md",
    "Portafolio de Microseguros.md",
    "Procedimientos Operativos.md",
    "Productos de Crédito.md",
)


def _corpus() -> object:
    return cargar_corpus(directorio=DATA, permitidos=PERMITIDOS)


def test_una_pregunta_que_cruza_dominios_selecciona_varios_documentos() -> None:
    seleccion = seleccionar_documentos(
        _corpus(),
        "¿Qué cubre el seguro de muerte accidental y cuál es el monto máximo "
        "del Crédito Agro Crece?",
    )

    nombres = {documento.nombre for documento in seleccion.documentos}
    assert "Portafolio de Microseguros.md" in nombres
    assert "Productos de Crédito.md" in nombres


def test_una_pregunta_de_un_solo_dominio_no_arrastra_documentos() -> None:
    seleccion = seleccionar_documentos(
        _corpus(), "¿Cuál es el monto máximo del Crédito Productivo Impulso?"
    )

    assert [documento.nombre for documento in seleccion.documentos] == [
        "Productos de Crédito.md"
    ]


def test_una_consulta_fuera_del_corpus_no_selecciona_nada() -> None:
    seleccion = seleccionar_documentos(_corpus(), "¿Cuál es el clima en Marte?")

    assert seleccion.vacia
