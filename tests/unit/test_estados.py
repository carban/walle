"""Pruebas de los estados de respuesta."""

from __future__ import annotations

import pytest

from walle.dominio.estados import (
    MENSAJE_BLOQUEADO,
    MENSAJE_SIN_INFORMACION,
    Estado,
    es_mensaje_sin_informacion,
)


def test_existen_exactamente_tres_estados() -> None:
    assert {estado.value for estado in Estado} == {
        "Exitosa",
        "Sin información suficiente",
        "Bloqueada por seguridad",
    }


def test_valores_literales() -> None:
    assert Estado.EXITOSA == "Exitosa"
    assert Estado.SIN_INFORMACION_SUFICIENTE == "Sin información suficiente"
    assert Estado.BLOQUEADA_POR_SEGURIDAD == "Bloqueada por seguridad"


def test_mensajes_canonicos() -> None:
    assert MENSAJE_SIN_INFORMACION == "No tengo información suficiente para responder."
    assert "información clasificada" in MENSAJE_BLOQUEADO


@pytest.mark.parametrize(
    "texto",
    [
        "No tengo información suficiente para responder.",
        "no tengo informacion suficiente para responder.",
        "NO TENGO INFORMACIÓN SUFICIENTE PARA RESPONDER.",
        "No tengo información suficiente para responder.\n\nFuente: «Productos.md».",
    ],
)
def test_detecta_mensaje_canonico_con_variantes(texto: str) -> None:
    assert es_mensaje_sin_informacion(texto)


def test_no_confunde_otros_textos_con_el_canonico() -> None:
    assert not es_mensaje_sin_informacion("Tengo información suficiente para responder.")
