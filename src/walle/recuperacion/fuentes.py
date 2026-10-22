"""Construccion de las fuentes citadas en la respuesta.

Una fuente dice de que documento y de que seccion proviene la respuesta; es lo que
permite al asesor verificar la informacion y a la politica de atencion exigir que
toda respuesta cite su origen.
"""

from __future__ import annotations

from walle.recuperacion.relevance import Seleccion


def construir_fuentes(seleccion: Seleccion) -> list[dict[str, str]]:
    """Devuelve la lista de fuentes (documento + fragmento) de una seleccion.

    Se deduplican las fuentes que apuntan al mismo documento y se conserva el orden
    de relevancia.
    """
    fuentes: list[dict[str, str]] = []
    vistos: set[str] = set()

    for resultado in seleccion.resultados:
        if resultado.documento.nombre in vistos:
            continue
        vistos.add(resultado.documento.nombre)
        fragmento = " | ".join(resultado.secciones) if resultado.secciones else "Contenido"
        fuentes.append({"documento": resultado.documento.nombre, "fragmento": fragmento})

    return fuentes
