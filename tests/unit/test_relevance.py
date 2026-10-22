"""Pruebas de la seleccion de documentos relevantes."""

from __future__ import annotations

from pathlib import Path

from walle.recuperacion.corpus import cargar_corpus
from walle.recuperacion.relevance import (
    expandir_conceptos,
    seleccionar_documentos,
    tokenizar,
)

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


def test_tokenizar_descarta_palabras_vacias() -> None:
    tokens = tokenizar("¿Cuál es el monto máximo del crédito?")

    assert "cual" not in tokens
    assert "monto" in tokens
    assert "credito" in tokens


def test_expandir_conceptos_agrega_sinonimos() -> None:
    conceptos = expandir_conceptos(["monto"])

    assert "limite" in conceptos
    assert "maximo" in conceptos


def test_selecciona_productos_de_credito() -> None:
    seleccion = seleccionar_documentos(
        _corpus(), "¿Cuál es el monto máximo del Crédito Productivo Impulso?"
    )

    assert not seleccion.vacia
    assert seleccion.documentos[0].nombre == "Productos de Crédito.md"


def test_selecciona_microseguros() -> None:
    seleccion = seleccionar_documentos(
        _corpus(), "¿Cuánto cubre el seguro de muerte accidental?"
    )

    assert not seleccion.vacia
    assert "Portafolio de Microseguros.md" in {
        documento.nombre for documento in seleccion.documentos
    }


def test_consulta_fuera_del_corpus_no_selecciona() -> None:
    seleccion = seleccionar_documentos(_corpus(), "¿Cuál es el clima en Marte?")

    assert seleccion.vacia


def test_umbral_alto_no_selecciona() -> None:
    seleccion = seleccionar_documentos(
        _corpus(), "¿Cuál es el monto máximo del Crédito Productivo Impulso?", umbral=99
    )

    assert seleccion.vacia


def test_pregunta_vacia_no_selecciona() -> None:
    seleccion = seleccionar_documentos(_corpus(), "   ")

    assert seleccion.vacia


def test_seleccion_incluye_secciones_coincidentes() -> None:
    seleccion = seleccionar_documentos(
        _corpus(), "¿Cuál es el monto máximo del Crédito Productivo Impulso?"
    )

    assert seleccion.resultados[0].secciones
