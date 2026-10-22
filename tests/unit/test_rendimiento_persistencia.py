"""Prueba informativa de rendimiento de la persistencia.

No falla por regimen estricto: mide y registra la duracion para poder comparar
entre ejecuciones. Solo falla si el rendimiento se degrada de forma grosera.
"""

from __future__ import annotations

import time
from pathlib import Path

from walle.dominio.estados import Estado
from walle.persistencia.modelo import Consulta
from walle.persistencia.repositorio import RepositorioSQLite

LIMITE_ESCRITURA_MS = 50.0
LIMITE_LECTURA_MS = 500.0


def _consulta(indice: int) -> Consulta:
    return Consulta(
        id=None,
        pregunta=f"¿Cuál es el monto máximo del crédito {indice}?",
        fecha_hora=f"2026-10-21T10:{indice % 60:02d}:00+00:00",
        respuesta="El monto máximo es $50.000.000.",
        fuentes=[{"documento": "Productos de Crédito.md", "fragmento": "Condiciones"}],
        estado=Estado.EXITOSA,
        duracion_ms=100,
        modelo="cohere/north-mini-code:free",
    )


def test_escritura_y_lectura_de_1000_consultas(tmp_path: Path) -> None:
    repositorio = RepositorioSQLite(tmp_path / "walle.db")

    inicio = time.perf_counter()
    for indice in range(1000):
        repositorio.registrar(_consulta(indice))
    escritura_ms = (time.perf_counter() - inicio) * 1000

    inicio = time.perf_counter()
    historial = repositorio.listar()
    lectura_ms = (time.perf_counter() - inicio) * 1000

    assert len(historial) == 1000
    assert escritura_ms < LIMITE_ESCRITURA_MS * 20, f"escritura lenta: {escritura_ms:.1f} ms"
    assert lectura_ms < LIMITE_LECTURA_MS, f"lectura lenta: {lectura_ms:.1f} ms"
