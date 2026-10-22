"""Carga del corpus documental en memoria.

Los documentos son pequenos, por lo que se cargan completos y se cachean. La carga
respeta una allowlist explicita: los archivos no listados nunca se abren.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

_ENCABEZADO = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Seccion:
    """Una seccion del documento, con su encabezado y su contenido."""

    titulo: str
    texto: str
    linea_inicial: int

    @property
    def clave(self) -> str:
        """Clave normalizada de la seccion, usada para localizar coincidencias."""
        return normalizar(self.titulo)


@dataclass(frozen=True)
class Documento:
    """Documento permitido del corpus."""

    nombre: str
    contenido: str
    secciones: tuple[Seccion, ...]
    hash_contenido: str

    @property
    def texto_normalizado(self) -> str:
        """Contenido normalizado para busquedas."""
        return normalizar(self.contenido)


@dataclass
class Corpus:
    """Conjunto de documentos permitidos, con control de duplicados."""

    documentos: tuple[Documento, ...] = field(default_factory=tuple)
    duplicados: tuple[str, ...] = field(default_factory=tuple)
    documentos_omitidos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def vacio(self) -> bool:
        """Indica si no hay documentos cargados."""
        return not self.documentos

    def por_nombre(self, nombre: str) -> Documento | None:
        """Devuelve el documento con ese nombre, si existe."""
        return next((doc for doc in self.documentos if doc.nombre == nombre), None)


def normalizar(texto: str) -> str:
    """Minusculas y sin acentos, para comparaciones resilientes."""
    import unicodedata

    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def hash_texto(contenido: str) -> str:
    """Huella estable del contenido normalizado de un documento."""
    return hashlib.sha256(normalizar(contenido).encode("utf-8")).hexdigest()


def dividir_secciones(contenido: str) -> tuple[Seccion, ...]:
    """Divide el contenido en secciones segun sus encabezados.

    El titulo de cada seccion es su ruta jerarquica completa
    ("Productos de Credito > Credito Productivo Impulso > Condiciones"), que es
    exactamente el fragmento que se cita como fuente.
    """
    secciones: list[Seccion] = []
    pila: list[tuple[int, str]] = []
    titulo_actual = "Contenido"
    lineas_actual: list[str] = []
    linea_inicial = 1

    for numero, linea in enumerate(contenido.splitlines(), start=1):
        coincidencia = _ENCABEZADO.match(linea)
        if coincidencia:
            if lineas_actual or secciones:
                secciones.append(
                    Seccion(
                        titulo=titulo_actual,
                        texto="\n".join(lineas_actual).strip(),
                        linea_inicial=linea_inicial,
                    )
                )
            nivel = len(coincidencia.group(1))
            titulo = coincidencia.group(2).strip()
            while pila and pila[-1][0] >= nivel:
                pila.pop()
            pila.append((nivel, titulo))
            titulo_actual = " > ".join(texto for _, texto in pila)
            lineas_actual = []
            linea_inicial = numero + 1
            continue
        lineas_actual.append(linea)

    secciones.append(
        Seccion(
            titulo=titulo_actual,
            texto="\n".join(lineas_actual).strip(),
            linea_inicial=linea_inicial,
        )
    )
    return tuple(secciones)


def cargar_corpus(
    directorio: Path,
    permitidos: tuple[str, ...],
    excluidos: tuple[str, ...] = (),
) -> Corpus:
    """Carga los documentos permitidos del directorio, ignorando duplicados.

    Los archivos excluidos y los que no estan en la allowlist no se abren.
    """
    documentos: list[Documento] = []
    duplicados: list[str] = []
    omitidos: list[str] = []
    hashes: dict[str, str] = {}

    for nombre in permitidos:
        if nombre in excluidos:
            omitidos.append(nombre)
            continue
        ruta = directorio / nombre
        if not ruta.is_file():
            omitidos.append(nombre)
            continue
        contenido = ruta.read_text(encoding="utf-8")
        huella = hash_texto(contenido)
        if huella in hashes:
            duplicados.append(nombre)
            continue
        hashes[huella] = nombre
        documentos.append(
            Documento(
                nombre=nombre,
                contenido=contenido,
                secciones=dividir_secciones(contenido),
                hash_contenido=huella,
            )
        )

    return Corpus(
        documentos=tuple(documentos),
        duplicados=tuple(duplicados),
        documentos_omitidos=tuple(omitidos),
    )
