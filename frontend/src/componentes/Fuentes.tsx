import type { Fuente } from '../tipos'

/** Bloque de referencias que sustentan la respuesta. */
export function Fuentes({ fuentes }: { fuentes: Fuente[] }) {
  if (fuentes.length === 0) return null

  return (
    <section className="fuentes" aria-label="Fuentes">
      <h3 className="fuentes__titulo">Fuentes</h3>
      <ul className="fuentes__lista">
        {fuentes.map((fuente) => (
          <li key={`${fuente.documento}-${fuente.fragmento}`} className="fuentes__item">
            <span className="fuentes__documento">{fuente.documento}</span>
            <span className="fuentes__fragmento">{fuente.fragmento}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
