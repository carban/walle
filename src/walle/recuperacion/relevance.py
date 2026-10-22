"""Seleccion del documento relevante para una pregunta.

La relevancia usa BM25 (Okapi BM25) para puntuar documentos y secciones,
con normalizacion de plurales y bonificaciones de sinonimos, entidades del
dominio y moneda. El resultado son los documentos a enviar al modelo y las
secciones que los sustentan, que despues se convierten en fuentes citadas.
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

#: Tope de secciones citadas por documento para que la fuente sea legible.
_MAX_SECCIONES = 3

#: Una seccion se cita solo si su puntaje no baja de la mitad del mejor.
_MARGEN_SECCIONES = 0.5

#: Consonantes que en espanol forman el plural con "es" (reclamacion -> reclamaciones).
_CONSONANTES_PLURAL_ES = frozenset("lrndzjs")


def normalizar_plural(token: str) -> str:
    """Reduce un plural en espanol a una forma estable para el indice BM25.

    BM25 compara tokens exactos: sin esta normalizacion "reclamacion" y
    "reclamaciones" nunca coinciden y la recuperacion depende del bonus de
    sinonimos. Las reglas son conservadoras a proposito: solo quitan
    terminaciones plurales productivas y dejan intactas palabras que ya
    terminan en "s" (pais, crisis, virus).
    """
    if len(token) <= 3 or not token.endswith("s"):
        return token
    if token.endswith("ces") and len(token) > 4:
        # veces -> vez, voces -> voz, raices -> raiz
        return token[:-3] + "z"
    if token.endswith("es") and len(token) > 4:
        candidato = token[:-2]
        if candidato[-1] in _CONSONANTES_PLURAL_ES:
            # intereses -> interes -> inter; paises -> pais.
            return normalizar_plural(candidato)
    if token.endswith(("is", "us")):
        return token
    return token[:-1]


def _stems(tokens: list[str]) -> set[str]:
    """Devuelve los stems de una lista de tokens."""
    return {normalizar_plural(t) for t in tokens}


def tokenizar(texto: str) -> list[str]:
    """Divide el texto en tokens normalizados y sin palabras vacias."""
    normalizado = normalizar(texto)
    tokens = _TOKEN.findall(normalizado)
    return [token for token in tokens if token not in _PALABRAS_VACIAS and len(token) > 1]


def tokenizar_indice(texto: str) -> list[str]:
    """Tokeniza y normaliza plurales para indexar y consultar con BM25."""
    return [normalizar_plural(token) for token in tokenizar(texto)]


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
    """Devuelve las secciones que mejor sustentan la pregunta, de mayor a menor.

    Se indexa el titulo junto con el texto porque el encabezado es parte de la
    evidencia ("Vida Protegida" no vuelve a decir "vida" en su contenido). Las
    secciones vacias se descartan para no citar encabezados sin informacion.
    """
    if not documento.secciones or not terminos:
        return ()

    secciones = [
        (indice, seccion)
        for indice, seccion in enumerate(documento.secciones)
        if seccion.texto.strip()
    ]
    if not secciones:
        return ()

    terminos_indice = [normalizar_plural(termino) for termino in terminos]

    indice_bm25 = BM25Index()
    for indice, seccion in secciones:
        # Se omite el titulo del documento ("Politicas de Atencion > ...") porque
        # repetirlo en todas las secciones baja el IDF y diluye las coincidencias.
        titulo_util = seccion.titulo.split(" > ", 1)[-1]
        indice_bm25.agregar(
            str(indice), tokenizar_indice(f"{titulo_util} {seccion.texto}")
        )

    scores = indice_bm25.scores(terminos_indice)
    ordenados = sorted(
        ((scores.get(str(indice), 0.0), indice) for indice, _ in secciones),
        key=lambda elemento: (-elemento[0], elemento[1]),
    )

    mejor = ordenados[0][0]
    if mejor <= 0:
        # Sin coincidencia en el contenido, se cita la primera seccion con texto.
        return (secciones[0][1].titulo,)

    corte = mejor * _MARGEN_SECCIONES
    return tuple(
        documento.secciones[indice].titulo
        for puntaje, indice in ordenados
        if puntaje >= corte
    )[:_MAX_SECCIONES]


def _bonificacion_sinonimos(
    tokens: list[str],
    documento: Documento,
    pesos: dict[str, float] | None = None,
) -> float:
    """Devuelve un impulso por coincidencia de grupos de sinonimos consulta-documento.

    El peso depende de la frecuencia documental del termino de la consulta: un
    termino presente en todos los documentos ("documentos") no distingue a
    ninguno y suma poco; un termino ausente del corpus ("siniestro") conserva
    todo el impulso. Asi se recuperan sinonimos sin que una palabra generica
    arrastre el corpus completo.
    """
    contenido_tokens = _stems(tokenizar(documento.contenido))
    consulta_stems = _stems(tokens)
    bonificacion = 0.0
    for grupo in _GRUPOS_SINONIMOS:
        grupo_stems = _stems(list(grupo))
        coincidentes = consulta_stems & grupo_stems
        if not coincidentes:
            continue
        if not (contenido_tokens & grupo_stems):
            continue
        if pesos is None:
            bonificacion += 1.0
        else:
            bonificacion += max(pesos.get(stem, 1.0) for stem in coincidentes)
    return bonificacion


def evaluar_documento(
    documento: Documento,
    tokens: list[str],
    puntaje_bm25: float = 0.0,
    pesos_sinonimos: dict[str, float] | None = None,
) -> ResultadoRelevancia:
    """Calcula el puntaje de relevancia de un documento y las secciones que coinciden.

    El puntaje combina el score BM25 del documento con bonificaciones por
    sinonimos, entidades del dominio y moneda. Las secciones se eligen mediante
    un indice BM25 interno sobre el titulo y el texto de cada seccion.
    """
    puntaje = puntaje_bm25

    # Coincidencia de sinonimos del dominio entre consulta y documento.
    puntaje += _bonificacion_sinonimos(tokens, documento, pesos_sinonimos)

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


def _pesos_por_frecuencia(
    tokens_indice: list[str],
    documentos_tokens: dict[str, list[str]],
) -> dict[str, float]:
    """Pondera cada termino de la consulta por su frecuencia documental.

    Un termino que aparece en todos los documentos no ayuda a discriminarlos:
    su peso baja y no puede, por si solo, superar el umbral. Un termino ausente
    del corpus (un sinonimo que el usuario uso) conserva el peso completo.
    """
    conjuntos = [set(tokens) for tokens in documentos_tokens.values()]
    return {
        token: 1.0 / (1.0 + sum(1 for conjunto in conjuntos if token in conjunto))
        for token in set(tokens_indice)
    }


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

    tokens_indice = [normalizar_plural(token) for token in tokens]

    # Indice BM25 a nivel documento: cada documento es una entrada.
    documentos_tokens = {
        documento.nombre: tokenizar_indice(documento.contenido)
        for documento in corpus.documentos
    }
    indice_documentos = BM25Index()
    for documento in corpus.documentos:
        indice_documentos.agregar(
            documento.nombre, documentos_tokens[documento.nombre]
        )

    scores_documentos = indice_documentos.scores(tokens_indice)
    pesos_sinonimos = _pesos_por_frecuencia(tokens_indice, documentos_tokens)

    resultados: list[ResultadoRelevancia] = []
    for documento in corpus.documentos:
        puntaje_bm25 = scores_documentos.get(documento.nombre, 0.0)
        resultado = evaluar_documento(
            documento,
            tokens,
            puntaje_bm25=puntaje_bm25,
            pesos_sinonimos=pesos_sinonimos,
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
