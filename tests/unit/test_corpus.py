"""Pruebas del corpus documental."""

from __future__ import annotations

from pathlib import Path

from walle.recuperacion.corpus import cargar_corpus, dividir_secciones, normalizar

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "Data"


def test_carga_solo_documentos_permitidos() -> None:
    corpus = cargar_corpus(
        directorio=DATA,
        permitidos=("Productos de Crédito.md",),
        excluidos=("Información restringida.md",),
    )

    assert [documento.nombre for documento in corpus.documentos] == ["Productos de Crédito.md"]
    assert "Información restringida.md" not in {
        documento.nombre for documento in corpus.documentos
    }


def test_documento_restringido_nunca_se_abre(tmp_path: Path) -> None:
    restringido = tmp_path / "Información restringida.md"
    restringido.write_text("SECRETO\n", encoding="utf-8")

    corpus = cargar_corpus(
        directorio=tmp_path,
        permitidos=("Información restringida.md",),
        excluidos=("Información restringida.md",),
    )

    assert corpus.documentos == ()
    assert corpus.vacio


def test_documentos_duplicados_se_cargan_una_vez(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("Contenido identico\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("Contenido identico\n", encoding="utf-8")

    corpus = cargar_corpus(
        directorio=tmp_path,
        permitidos=("a.md", "b.md"),
    )

    assert len(corpus.documentos) == 1
    assert corpus.duplicados == ("b.md",)


def test_archivo_inexistente_se_omite(tmp_path: Path) -> None:
    corpus = cargar_corpus(directorio=tmp_path, permitidos=("no-existe.md",))

    assert corpus.documentos == ()
    assert corpus.documentos_omitidos == ("no-existe.md",)


def test_corpus_vacio_no_falla(tmp_path: Path) -> None:
    corpus = cargar_corpus(directorio=tmp_path, permitidos=())

    assert corpus.vacio


def test_dividir_secciones_detecta_encabezados() -> None:
    secciones = dividir_secciones("# Titulo\ntexto\n## Subtitulo\nmas texto\n")

    assert [seccion.titulo for seccion in secciones] == ["Titulo", "Titulo > Subtitulo"]
    assert "mas texto" in secciones[1].texto


def test_normalizar_quita_acentos() -> None:
    assert normalizar("Crédito Agro Crece") == "credito agro crece"
