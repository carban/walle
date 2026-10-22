"""Seleccion del documento relevante para una pregunta.

La relevancia es lexica pero no ingenua: normaliza acentos, descarta palabras vacias,
agrupa sinonimos del dominio y premia la coincidencia de entidades (productos,
montos, plazos). El resultado son los documentos a enviar al modelo y las secciones
que los sustentan, que despues se convierten en fuentes citadas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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


def evaluar_documento(
    documento: Documento, tokens: list[str], conceptos: set[str]
) -> ResultadoRelevancia:
    """Calcula el puntaje de relevancia de un documento y las secciones que coinciden."""
    texto = documento.texto_normalizado
    presentes = set(tokenizar(documento.contenido))
    coincidencias = {token for token in tokens if token in presentes}
    puntaje = float(len(coincidencias))

    # Los sinonimos amplian el alcance: una sola coincidencia conceptual ya es senal.
    conceptuales = {token for token in conceptos if token in presentes}
    if conceptuales and not coincidencias:
        puntaje = 1.0

    # Las entidades del dominio (nombres de producto) son muy discriminantes.
    pregunta_normalizada = normalizar(" ".join(tokens))
    for entidad in _ENTIDADES:
        if entidad in pregunta_normalizada and entidad in texto:
            puntaje += 1.5
            break

    if _MONEDA.search(documento.contenido) and "$" in " ".join(tokens):
        puntaje += 0.5

    # Las secciones que mas aportan se citan primero; el resto no aporta al asesor.
    # El titulo pesa mas que el cuerpo: "Credito Agro Crece" no responde a una
    # pregunta sobre "Credito Productivo Impulso".
    coincidencias_por_seccion: list[tuple[int, str]] = []
    for seccion in documento.secciones:
        texto_seccion = normalizar(seccion.texto)
        en_titulo = sum(1 for token in coincidencias if token in seccion.clave)
        en_texto = sum(1 for token in coincidencias if token in texto_seccion)
        total = 2 * en_titulo + en_texto
        if total:
            coincidencias_por_seccion.append((total, seccion.titulo))
    coincidencias_por_seccion.sort(key=lambda elemento: (-elemento[0], elemento[1]))

    if not coincidencias_por_seccion:
        secciones: tuple[str, ...] = (
            (documento.secciones[0].titulo,) if documento.secciones else ()
        )
    else:
        mejor = coincidencias_por_seccion[0][0]
        # Solo se citan las secciones que igualan el mejor puntaje.
        secciones = tuple(
            titulo for total, titulo in coincidencias_por_seccion if total == mejor
        )

    return ResultadoRelevancia(documento=documento, puntaje=puntaje, secciones=secciones)


def seleccionar_documentos(
    corpus: Corpus,
    pregunta: str,
    umbral: float = 1.0,
    margen_relativo: float = 0.3,
) -> Seleccion:
    """Selecciona los documentos relevantes para la pregunta.

    Se queda con los documentos que superan el umbral minimo y, entre ellos, con los
    que alcanzan un porcentaje del mejor resultado. Ese margen relativo permite que
    una pregunta que cruza dos dominios (por ejemplo, un seguro y un credito)
    llegue al modelo con ambos documentos y no solo con el mas relevante.
    """
    tokens = tokenizar(pregunta)
    if not tokens:
        return Seleccion()

    conceptos = expandir_conceptos(tokens)
    resultados = [
        evaluar_documento(documento, tokens, conceptos) for documento in corpus.documentos
    ]
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
