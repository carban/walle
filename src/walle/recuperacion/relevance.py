"""Seleccion del documento relevante para una pregunta.

La relevancia usa BM25 (Okapi BM25) para puntuar documentos y secciones,
complementado con bonificaciones de entidades del dominio y moneda. El
resultado son los documentos a enviar al modelo y las secciones que los
sustentan, que despues se convierten en fuentes citadas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from walle.recuperacion.bm25 import BM25Index
from walle.recuperacion.corpus import Corpus, Documento, normalizar

# Palabras sin valor discriminante en el dominio.
_PALABRAS_VACIAS = frozenset(
    {
        "a",
        "al",
        "algo",
        "ante",
        "antes",
        "aqui",
        "asi",
        "cada",
        "como",
        "con",
        "contra",
        "cual",
        "cuales",
        "cuando",
        "cuanto",
        "de",
        "del",
        "desde",
        "donde",
        "durante",
        "e",
        "el",
        "ella",
        "ellos",
        "en",
        "entre",
        "es",
        "esa",
        "ese",
        "eso",
        "esta",
        "este",
        "esto",
        "esos",
        "estas",
        "fue",
        "ha",
        "hay",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "me",
        "mi",
        "mis",
        "mucho",
        "muy",
        "nada",
        "no",
        "nos",
        "o",
        "otro",
        "para",
        "pero",
        "poco",
        "por",
        "porque",
        "que",
        "quien",
        "se",
        "sea",
        "segun",
        "ser",
        "si",
        "sin",
        "sobre",
        "son",
        "su",
        "sus",
        "tambien",
        "tiene",
        "todo",
        "tu",
        "un",
        "una",
        "uno",
        "unos",
        "y",
        "ya",
    }
)

# Sinonimos del dominio: cada grupo representa el mismo concepto.
_GRUPOS_SINONIMOS: tuple[frozenset[str], ...] = (
    frozenset({"credito", "prestamo", "financiacion"}),
    frozenset({"microseguro", "seguro", "seguros", "poliza", "aseguramiento"}),
    frozenset({"monto", "limite", "maximo", "valor", "cantidad", "capital", "cobertura"}),
    frozenset({"plazo", "meses", "duracion", "periodo", "vigencia"}),
    frozenset({"reclamacion", "reclamo", "reclamaciones", "siniestro", "indemnizacion"}),
    frozenset({"requisito", "requisitos", "documentacion", "documentos", "soportes"}),
    frozenset({"edad", "anos", "rango", "edad_minima", "edad_maxima"}),
    frozenset({"beneficio", "beneficios", "coberturas", "inclusiones"}),
    frozenset({"procedimiento", "proceso", "pasos", "etapas"}),
    frozenset({"politica", "politicas", "norma", "normas", "regla", "reglas"}),
    frozenset({"tiempo", "dias", "habiles", "plazo_estimado"}),
    frozenset({"tasa", "interes", "intereses"}),
    frozenset({"pqr", "queja", "reclamo", "solicitud"}),
)

# Entidades del dominio: aparecen literalmente en los documentos.
_ENTIDADES = (
    "credito productivo impulso",
    "credito agro crece",
    "credito mujer emprende",
    "vida protegida",
    "accidente personal esencial",
    "negocio seguro",
    "portafolio",
    "microseguros",
    "asesor comercial",
)

_TOKEN = re.compile(r"[a-z0-9]+")
_MONEDA = re.compile(r"\$\s?[\d.,]+")


def _stem_token(token: str) -> str:
    """Stemmer muy sencillo: quita la 's' final de plurales en espanol.

    Sirve para que "procedimientos" coincida con el grupo de sinonimos que tiene
    "procedimiento", sin tener que listar todas las formas plurales a mano.
    """
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _stems(tokens: list[str]) -> set[str]:
    """Devuelve los stems de una lista de tokens."""
    return {_stem_token(t) for t in tokens}


def tokenizar(texto: str) -> list[str]:
    """Divide el texto en tokens normalizados y sin palabras vacias."""
    normalizado = normalizar(texto)
    tokens = _TOKEN.findall(normalizado)
    return [token for token in tokens if token not in _PALABRAS_VACIAS and len(token) > 1]


def expandir_conceptos(tokens: list[str]) -> set[str]:
    """Anade a los tokens los sinonimos de su grupo, para tolerar distintas formas."""
    conceptos = set(tokens)
    for grupo in _GRUPOS_SINONIMOS:
        if conceptos & grupo:
            conceptos |= grupo
    return conceptos


@dataclass(frozen=True)
class ResultadoRelevancia:
    """Resultado de evaluar un documento frente a una pregunta."""

    documento: Documento
    puntaje: float
    secciones: tuple[str, ...]

    @property
    def relevante(self) -> bool:
        """Indica si el documento supera el umbral minimo."""
        return self.puntaje > 0


@dataclass(frozen=True)
class Seleccion:
    """Documentos seleccionados para responder una pregunta."""

    resultados: tuple[ResultadoRelevancia, ...] = ()
    puntaje_maximo: float = 0.0

    @property
    def vacia(self) -> bool:
        """Indica que no hay documento relevante."""
        return not self.resultados

    @property
    def documentos(self) -> tuple[Documento, ...]:
        """Documentos seleccionados, en orden de relevancia."""
        return tuple(resultado.documento for resultado in self.resultados)


def _secciones_bm25(documento: Documento, terminos: list[str]) -> tuple[str, ...]:
    """Devuelve las secciones del documento ordenadas por su puntaje BM25.

    Cada seccion se indexa de forma independiente con BM25 y se devuelven las
    que tienen coincidencia (score > 0), ordenadas de mayor a menor relevancia.
    Si ninguna seccion coincide, se devuelve la primera seccion como fallback.
    """
    if not documento.secciones or not terminos:
        return ()

    indice = BM25Index()
    secciones_lista = list(documento.secciones)
    for indice_seccion, seccion in enumerate(secciones_lista):
        seccion_tokens = tokenizar(seccion.texto)
        indice.agregar(str(indice_seccion), seccion_tokens)

    scores = indice.scores(terminos)
    ordenados = sorted(scores.items(), key=lambda elemento: (-elemento[1], int(elemento[0])))

    coincidentes = tuple(
        secciones_lista[int(identificador)].titulo
        for identificador, score in ordenados
        if score > 0
    )

    if not coincidentes:
        return (documento.secciones[0].titulo,) if documento.secciones else ()

    return coincidentes


def _bonificacion_sinonimos(tokens: list[str], documento: Documento) -> float:
    """Devuelve un impulso por coincidencia de grupos de sinonimos consulta-documento.

    Si la consulta tiene al menos un token de un grupo de sinonimos y el documento
    tiene al menos un token del mismo grupo, se suma un impulso fijo. Esto permite
    recuperar documentos cuando el usuario usa un sinonimo del termino que aparece
    en el documento (ej. "procedimiento" vs "procedimientos"), sin el ruido de
    expandir todos los sinonimos en el indice BM25.
    """
    contenido_tokens = _stems(tokenizar(documento.contenido))
    consulta_stems = _stems(tokens)
    bonificacion = 0.0
    for grupo in _GRUPOS_SINONIMOS:
        grupo_stems = _stems(list(grupo))
        consulta_en_grupo = bool(consulta_stems & grupo_stems)
        documento_en_grupo = bool(contenido_tokens & grupo_stems)
        if consulta_en_grupo and documento_en_grupo:
            bonificacion += 1.0
    return bonificacion


def evaluar_documento(
    documento: Documento,
    tokens: list[str],
    puntaje_bm25: float = 0.0,
) -> ResultadoRelevancia:
    """Calcula el puntaje de relevancia de un documento y las secciones que coinciden.

    El puntaje combina el score BM25 del documento con bonificaciones por
    entidades del dominio y por moneda. Las secciones se eligen mediante un
    indice BM25 interno sobre las secciones del mismo documento.
    """
    puntaje = puntaje_bm25

    # Coincidencia de sinonimos del dominio entre consulta y documento.
    puntaje += _bonificacion_sinonimos(tokens, documento)

    # Las entidades del dominio (nombres de producto) son muy discriminantes.
    pregunta_normalizada = normalizar(" ".join(tokens))
    for entidad in _ENTIDADES:
        if entidad in pregunta_normalizada and entidad in documento.texto_normalizado:
            puntaje += 1.5
            break

    if _MONEDA.search(documento.contenido) and "$" in " ".join(tokens):
        puntaje += 0.5

    # Las secciones se eligen por su puntaje BM25 interno dentro del documento.
    # Se usan los tokens originales (sin expansion de sinonimos) para evitar
    # que terminos expandidos marquen secciones irrelevantes.
    secciones = _secciones_bm25(documento, tokens)

    return ResultadoRelevancia(documento=documento, puntaje=puntaje, secciones=secciones)


def seleccionar_documentos(
    corpus: Corpus,
    pregunta: str,
    umbral: float = 1.0,
    margen_relativo: float = 0.3,
) -> Seleccion:
    """Selecciona los documentos relevantes para la pregunta usando BM25.

    Se construye un indice BM25 sobre el contenido completo de cada documento
    del corpus. Luego se filtra por umbral absoluto y, entre los que lo
    superan, por un margen relativo del mejor resultado. Ese margen relativo
    permite que una pregunta que cruza dos dominios (por ejemplo, un seguro y
    un credito) llegue al modelo con ambos documentos y no solo con el mas
    relevante.
    """
    tokens = tokenizar(pregunta)
    if not tokens:
        return Seleccion()

    # Indice BM25 a nivel documento: cada documento es una entrada.
    indice_documentos = BM25Index()
    for documento in corpus.documentos:
        doc_tokens = tokenizar(documento.contenido)
        indice_documentos.agregar(documento.nombre, doc_tokens)

    scores_documentos = indice_documentos.scores(tokens)

    resultados: list[ResultadoRelevancia] = []
    for documento in corpus.documentos:
        puntaje_bm25 = scores_documentos.get(documento.nombre, 0.0)
        resultado = evaluar_documento(
            documento, tokens, puntaje_bm25=puntaje_bm25
        )
        resultados.append(resultado)

    relevantes = [resultado for resultado in resultados if resultado.puntaje >= umbral]
    if not relevantes:
        return Seleccion()

    mejor = max(resultado.puntaje for resultado in relevantes)
    corte = max(umbral, mejor * margen_relativo)
    seleccionados = tuple(
        resultado for resultado in relevantes if resultado.puntaje >= corte
    )
    seleccionados = tuple(sorted(seleccionados, key=lambda resultado: -resultado.puntaje))
    return Seleccion(resultados=seleccionados, puntaje_maximo=mejor)
