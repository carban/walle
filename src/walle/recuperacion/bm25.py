"""Indice BM25 (Okapi BM25) para recuperacion de documentos y secciones.

BM25 pondera las coincidencias de terminos teniendo en cuenta:
- frecuencia del termino en el documento (con saturacion via k1),
- longitud del documento respecto al promedio (via b),
- frecuencia inversa de documento (IDF): terminos raros pesan mas que terminos comunes.

Dos instancias del indice se usan en la recuperacion:
- una a nivel documento (contenido completo) para seleccionar el documento;
- otra a nivel seccion (texto de cada seccion) para elegir la mejor seccion
  dentro del documento seleccionado.
"""

from __future__ import annotations

import math
from collections import defaultdict


class BM25Index:
    """Indice invertido BM25 para un conjunto de entradas (documentos o secciones)."""

    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        """Crea el indice con los parametros de saturacion k1 y longitud b."""
        self.k1 = k1
        self.b = b
        self._documentos: dict[str, list[str]] = {}
        self._longitudes: dict[str, int] = {}
        self._frecuencias: dict[str, dict[str, int]] = {}
        self._documentos_por_termino: dict[str, set[str]] = defaultdict(set)
        self._longitud_media: float = 0.0
        self._construido: bool = False

    def agregar(self, identificador: str, tokens: list[str]) -> None:
        """Registra una entrada (documento o seccion) con sus tokens ya tokenizados."""
        self._documentos[identificador] = list(tokens)
        self._construido = False

    def _construir(self) -> None:
        """Calcula longitudes, frecuencias, IDF y longitud media una sola vez."""
        if self._construido:
            return

        self._frecuencias = {}
        self._documentos_por_termino = defaultdict(set)
        total_longitud = 0

        for identificador, tokens in self._documentos.items():
            frecuencias: dict[str, int] = defaultdict(int)
            for token in tokens:
                frecuencias[token] += 1
                self._documentos_por_termino[token].add(identificador)
            self._frecuencias[identificador] = dict(frecuencias)
            longitud = len(tokens)
            self._longitudes[identificador] = longitud
            total_longitud += longitud

        n = len(self._documentos)
        self._longitud_media = total_longitud / n if n else 0.0
        self._construido = True

    def idf(self, termino: str) -> float:
        """Devuelve el IDF de un termino (0 si no aparece en ninguna entrada)."""
        self._construir()
        n = len(self._documentos)
        if n == 0:
            return 0.0
        nq = len(self._documentos_por_termino.get(termino, set()))
        # Variante estable: evita divisiones por cero y penaliza terminos en todos los docs.
        return math.log((n - nq + 0.5) / (nq + 0.5) + 1.0)

    def score(self, termino: str, identificador: str) -> float:
        """Puntaje BM25 de un solo termino para una entrada."""
        self._construir()
        if identificador not in self._documentos:
            return 0.0
        frecuencias = self._frecuencias.get(identificador, {})
        f = frecuencias.get(termino, 0)
        if f == 0:
            return 0.0
        longitud = self._longitudes[identificador]
        denominador = f + self.k1 * (1 - self.b + self.b * longitud / self._longitud_media)
        return self.idf(termino) * ((f * (self.k1 + 1)) / denominador)

    def score_todos(self, terminos: list[str], identificador: str) -> float:
        """Suma los puntajes BM25 de varios terminos para una entrada."""
        return sum(self.score(termino, identificador) for termino in terminos)

    def scores(self, terminos: list[str]) -> dict[str, float]:
        """Devuelve el puntaje BM25 de cada entrada para los terminos dados."""
        self._construir()
        return {
            identificador: self.score_todos(terminos, identificador)
            for identificador in self._documentos
        }

    def mejores(self, terminos: list[str], limite: int | None = None) -> list[tuple[str, float]]:
        """Devuelve las entradas mejor puntuadas para los terminos, ordenadas de mayor a menor."""
        todos = self.scores(terminos)
        ordenados = sorted(todos.items(), key=lambda elemento: (-elemento[1], elemento[0]))
        if limite is not None:
            return ordenados[:limite]
        return ordenados
