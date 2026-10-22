import type { Estado } from '../tipos'
import { Fuentes } from './Fuentes'

interface Props {
  pregunta: string
  respuesta: string
  estado: Estado
  fuentes: { documento: string; fragmento: string }[]
  duracionMs: number
  modelo: string
}

/** Par pregunta/respuesta dentro del chat. */
export function Intercambio({
  pregunta,
  respuesta,
  estado,
  fuentes,
  duracionMs,
  modelo,
}: Props) {
  return (
    <article className="intercambio">
      <div className="burbuja burbuja--usuario">
        <p className="burbuja__texto">{pregunta}</p>
      </div>

      <div className="burbuja burbuja--asistente">
        <header className="burbuja__cabecera">
          <span className={`etiqueta etiqueta--${slug(estado)}`}>{estado}</span>
          {modelo ? <span className="burbuja__meta">{modelo}</span> : null}
          <span className="burbuja__meta">{duracionMs} ms</span>
        </header>
        <p className="burbuja__texto">{respuesta}</p>
        <Fuentes fuentes={fuentes} />
      </div>
    </article>
  )
}

/** Convierte el estado en un identificador seguro para clases CSS. */
function slug(estado: Estado): string {
  return estado
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z]+/g, '-')
}
