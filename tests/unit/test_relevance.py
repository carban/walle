"""Pruebas de la seleccion de documentos relevantes."""

from __future__ import annotations

from pathlib import Path

from walle.recuperacion.corpus import cargar_corpus
from walle.recuperacion.relevance import (
    expandir_conceptos,
    normalizar_plural,
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


def test_normalizar_plural_une_singular_y_plural() -> None:
    assert normalizar_plural("reclamaciones") == normalizar_plural("reclamacion")
    assert normalizar_plural("procedimientos") == normalizar_plural("procedimiento")
    assert normalizar_plural("requisitos") == normalizar_plural("requisito")
    assert normalizar_plural("clientes") == normalizar_plural("cliente")


def test_normalizar_plural_respeta_palabras_terminadas_en_s() -> None:
    assert normalizar_plural("pais") == "pais"
    assert normalizar_plural("paises") == "pais"
    assert normalizar_plural("crisis") == "crisis"
    assert normalizar_plural("meses") == "mes"
    assert normalizar_plural("mes") == "mes"


def test_termino_generico_no_arrastra_todo_el_corpus() -> None:
    seleccion = seleccionar_documentos(_corpus(), "¿Qué requisitos hay?")

    assert [documento.nombre for documento in seleccion.documentos] == [
        "Productos de Crédito.md"
    ]


def test_documentos_necesito_prioriza_procedimientos() -> None:
    seleccion = seleccionar_documentos(_corpus(), "¿Qué documentos necesito?")

    nombres = [documento.nombre for documento in seleccion.documentos]
    assert nombres[0] == "Procedimientos Operativos.md"
    assert len(nombres) < 5


def test_sinonimo_ausente_del_corpus_sigue_recuperando() -> None:
    seleccion = seleccionar_documentos(_corpus(), "¿Qué cubre una póliza de vida?")

    assert "Portafolio de Microseguros.md" in {
        documento.nombre for documento in seleccion.documentos
    }
