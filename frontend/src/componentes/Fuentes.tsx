import type { Fuente as FuenteTipo } from '../tipos'

interface Props {
  fuentes: FuenteTipo[]
}

/**
 * Bloque de referencias que sustentan una respuesta (RF-03).
 *
 * No renderiza nada cuando la lista esta vacia: las respuestas sin fuentes
 * (insuficiencia o bloqueo) no muestran bloque de fuentes.
 */
export function Fuentes({ fuentes }: Props) {
  if (fuentes.length === 0) return null

  return (
    <div className="fuentes">
      <h4 className="fuentes__titulo">Fuentes</h4>
      <ul className="fuentes__lista">
        {fuentes.map((fuente, indice) => (
          <li className="fuentes__item" key={`${fuente.documento}-${indice}`}>
            <span className="fuentes__documento">{fuente.documento}</span>
            <span className="fuentes__fragmento">{fuente.fragmento}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
