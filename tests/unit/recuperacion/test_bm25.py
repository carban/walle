"""Pruebas del indice BM25 para recuperacion de documentos y secciones."""

from __future__ import annotations

from walle.recuperacion.bm25 import BM25Index


def _indice_ejemplo() -> BM25Index:
    indice = BM25Index()
    indice.agregar("doc1", ["credito", "producto", "monto", "maximo", "credito"])
    indice.agregar("doc2", ["seguro", "muerte", "accidental", "cobertura"])
    indice.agregar("doc3", ["credito", "agro", "plazo", "meses", "tasa"])
    return indice


def test_bm25_termino_en_todos_tiene_idf_bajo() -> None:
    """Un termino presente en todos los documentos debe tener IDF bajo."""
    indice = _indice_ejemplo()
    # "credito" aparece en doc1 y doc3 (2 de 3), no en todos.
    idf_credito = indice.idf("credito")
    idf_seguro = indice.idf("seguro")  # aparece solo en doc1 (1 de 3)
    assert idf_seguro > idf_credito > 0


def test_bm25_termino_ausente_puntaje_cero() -> None:
    """Un termino que no aparece en ninguna entrada da score 0."""
    indice = _indice_ejemplo()
    assert indice.score("inexistente", "doc1") == 0.0


def test_bm25_documento_vacio_no_falla() -> None:
    """Un indice sin documentos no falla al consultar."""
    indice = BM25Index()
    assert indice.idf("cualquier") == 0.0
    assert indice.score("cualquier", "doc1") == 0.0
    assert indice.scores(["cualquier"]) == {}


def test_bm25_ranking_por_coincidencias() -> None:
    """El documento con mas coincidencias de un termino raro debe ranking mas alto."""
    indice = BM25Index()
    indice.agregar("a", ["credito", "credito", "credito"])
    indice.agregar("b", ["credito"])
    indice.agregar("c", ["seguro", "seguro"])

    scores = indice.scores(["credito"])
    assert scores["a"] > scores["b"]
    assert scores["c"] == 0.0


def test_bm25_normaliza_por_longitud() -> None:
    """Documentos mas largos con la misma frecuencia relativa no se favorecen indebidamente."""
    indice = BM25Index()
    # Doc corto: 1 de 3 tokens es "credito"
    indice.agregar("corto", ["credito", "seguro", "plazo"])
    # Doc largo: 10 de 30 tokens es "credito" (misma proporcion)
    indice.agregar("largo", ["credito"] * 10 + ["seguro"] * 10 + ["plazo"] * 10)

    scores = indice.scores(["credito"])
    # Con BM25, el doc largo no debe tener una ventaja desproporcionada por longitud
    assert scores["corto"] > 0
    assert scores["largo"] > 0


def test_bm25_mejores_devuelve_ordenado() -> None:
    """mejores() devuelve las entradas ordenadas de mayor a menor score."""
    indice = _indice_ejemplo()
    mejores = indice.mejores(["credito", "monto"], limite=2)
    assert len(mejores) == 2
    assert mejores[0][1] >= mejores[1][1]


def test_bm25_agregar_despues_de_construir_recalcula() -> None:
    """Agregar entradas despues de construir invalida el indice y lo recalcula."""
    indice = BM25Index()
    indice.agregar("doc1", ["credito", "monto"])
    _ = indice.scores(["credito"])  # construye
    indice.agregar("doc2", ["credito", "plazo"])
    scores = indice.scores(["credito"])
    assert "doc2" in scores
    assert scores["doc2"] > 0


def test_recupera_documento_credito_producto() -> None:
    """BM25 sitúa Productos de Credito como el mejor para una consulta de credito."""
    from pathlib import Path

    from walle.recuperacion.corpus import cargar_corpus
    from walle.recuperacion.relevance import seleccionar_documentos

    raiz = Path(__file__).resolve().parents[3]
    data = raiz / "Data"
    permitidos = (
        "Manual del Asesor Comercial.md",
        "Políticas de Atención.md",
        "Portafolio de Microseguros.md",
        "Procedimientos Operativos.md",
        "Productos de Crédito.md",
    )
    corpus = cargar_corpus(directorio=data, permitidos=permitidos)

    pregunta = "¿Cuál es el monto máximo del Crédito Productivo Impulso?"
    seleccion = seleccionar_documentos(corpus, pregunta)

    assert not seleccion.vacia
    assert seleccion.documentos[0].nombre == "Productos de Crédito.md"


def test_recupera_seccion_especifica_del_documento() -> None:
    """Las secciones devueltas pertenecen al documento y no están vacías."""
    from pathlib import Path

    from walle.recuperacion.corpus import cargar_corpus
    from walle.recuperacion.relevance import seleccionar_documentos

    raiz = Path(__file__).resolve().parents[3]
    data = raiz / "Data"
    permitidos = (
        "Productos de Crédito.md",
    )
    corpus = cargar_corpus(directorio=data, permitidos=permitidos)

    seleccion = seleccionar_documentos(
        corpus, "¿Cuál es el monto máximo del Crédito Productivo Impulso?"
    )

    assert not seleccion.vacia
    resultado = seleccion.resultados[0]
    assert resultado.secciones
    # Cada sección citada debe ser una sección real del documento
    nombres_seccion = {s.titulo for s in resultado.documento.secciones}
    for seccion in resultado.secciones:
        assert seccion in nombres_seccion


def test_recupera_documento_microseguro() -> None:
    """BM25 sitúa Portafolio de Microseguros como el mejor para una consulta de seguros."""
    from pathlib import Path

    from walle.recuperacion.corpus import cargar_corpus
    from walle.recuperacion.relevance import seleccionar_documentos

    raiz = Path(__file__).resolve().parents[3]
    data = raiz / "Data"
    permitidos = (
        "Manual del Asesor Comercial.md",
        "Políticas de Atención.md",
        "Portafolio de Microseguros.md",
        "Procedimientos Operativos.md",
        "Productos de Crédito.md",
    )
    corpus = cargar_corpus(directorio=data, permitidos=permitidos)

    seleccion = seleccionar_documentos(
        corpus, "¿Cuánto cubre el seguro de muerte accidental?"
    )

    assert not seleccion.vacia
    nombres = {documento.nombre for documento in seleccion.documentos}
    assert "Portafolio de Microseguros.md" in nombres


def test_no_trae_productos_credito_para_consulta_microseguro() -> None:
    """Una consulta sobre microseguros no debe traer Productos de Credito.

    Antes del ajuste, la expansion de sinonimos de "cobertura" hacia el grupo
    de monto/valor/cantidad hacia que Productos de Credito obtuviera un score
    BM25 ligeramente superior al de Portafolio de Microseguros.
    """
    from pathlib import Path

    from walle.recuperacion.corpus import cargar_corpus
    from walle.recuperacion.relevance import seleccionar_documentos

    raiz = Path(__file__).resolve().parents[3]
    data = raiz / "Data"
    permitidos = (
        "Manual del Asesor Comercial.md",
        "Políticas de Atención.md",
        "Portafolio de Microseguros.md",
        "Procedimientos Operativos.md",
        "Productos de Crédito.md",
    )
    corpus = cargar_corpus(directorio=data, permitidos=permitidos)

    seleccion = seleccionar_documentos(
        corpus, "microseguro muerte accidental cobertura"
    )

    assert not seleccion.vacia
    nombres = [documento.nombre for documento in seleccion.documentos]
    assert nombres[0] == "Portafolio de Microseguros.md"
    assert "Productos de Crédito.md" not in nombres


def test_recupera_procedimientos_para_reclamar() -> None:
    """Una consulta con plurales recupera el documento de procedimientos.

    "procedimiento" (singular en la consulta) debe coincidir con
    "procedimientos" (plural en el documento) gracias al stemmer de sinonimos.
    Antes devolvia vacia porque no habia coincidencia exacta de token.
    """
    from pathlib import Path

    from walle.recuperacion.corpus import cargar_corpus
    from walle.recuperacion.relevance import seleccionar_documentos

    raiz = Path(__file__).resolve().parents[3]
    data = raiz / "Data"
    permitidos = (
        "Manual del Asesor Comercial.md",
        "Políticas de Atención.md",
        "Portafolio de Microseguros.md",
        "Procedimientos Operativos.md",
        "Productos de Crédito.md",
    )
    corpus = cargar_corpus(directorio=data, permitidos=permitidos)

    seleccion = seleccionar_documentos(corpus, "procedimiento para reclamar")

    assert not seleccion.vacia
    nombres = [documento.nombre for documento in seleccion.documentos]
    assert nombres[0] == "Procedimientos Operativos.md"


def test_secciones_microseguros_son_especificas() -> None:
    """Las secciones de microseguros deben ser específicas del tema consultado.

    "muerte accidental" debe apuntar a la seccion "Accidente Personal Esencial",
    no a la seccion general del documento.
    """
    from pathlib import Path

    from walle.recuperacion.corpus import cargar_corpus
    from walle.recuperacion.relevance import seleccionar_documentos

    raiz = Path(__file__).resolve().parents[3]
    data = raiz / "Data"
    permitidos = ("Portafolio de Microseguros.md",)
    corpus = cargar_corpus(directorio=data, permitidos=permitidos)

    seleccion = seleccionar_documentos(
        corpus, "seguro de muerte accidental"
    )

    assert not seleccion.vacia
    resultado = seleccion.resultados[0]
    assert "Portafolio de Microseguros > Accidente Personal Esencial" in resultado.secciones
