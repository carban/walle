"""Pruebas de la validacion de la entrada."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from walle.api.esquema import ConsultaRequest


def test_pregunta_valida_se_acepta() -> None:
    cuerpo = ConsultaRequest(pregunta="¿Cuál es el monto máximo del crédito?")

    assert cuerpo.pregunta.startswith("¿Cuál")


@pytest.mark.parametrize("pregunta", ["", "   ", "ab", "a" * 2001])
def test_pregunta_invalida_se_rechaza(pregunta: str) -> None:
    with pytest.raises(ValidationError):
        ConsultaRequest(pregunta=pregunta)


def test_pregunta_de_2000_caracteres_se_acepta() -> None:
    cuerpo = ConsultaRequest(pregunta="a" * 2000)

    assert len(cuerpo.pregunta) == 2000


def test_caracteres_de_control_se_rechazan() -> None:
    with pytest.raises(ValidationError):
        ConsultaRequest(pregunta="pregunta\x00con control")


def test_campos_ausentes_se_rechazan() -> None:
    with pytest.raises(ValidationError):
        ConsultaRequest()  # type: ignore[call-arg]
