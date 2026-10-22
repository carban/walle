import type { ReactNode } from 'react'
import type { Estado, Fuente } from '../tipos'
import { Fuentes } from './Fuentes'

interface Props {
  pregunta: string
  respuesta: string
  estado: Estado
  fuentes: Fuente[]
  duracionMs: number
  modelo: string
}

/**
 * Par pregunta/respuesta dentro del chat (RF-02).
 *
 * El texto se pinta tal cual lo devuelve la API: React escapa el contenido, asi
 * que no hay forma de inyectar HTML en el DOM (R-04).
 */
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
        <p className="burbuja__texto">{conNegritas(respuesta)}</p>
        <Fuentes fuentes={fuentes} />
      </div>
    </article>
  )
}

/**
 * Convierte las parejas `**texto**` en nodos <strong>.
 *
 * Se construyen nodos de React en lugar de HTML: el contenido del modelo sigue
 * escapandose por defecto y no se abre la puerta a inyeccion (R-04). Los
 * marcadores sin pareja se dejan literales para no alterar el texto original.
 */
function conNegritas(texto: string): ReactNode[] {
  const nodos: ReactNode[] = []
  let ultimo = 0

  for (const coincidencia of texto.matchAll(/\*\*(.+?)\*\*/g)) {
    const inicio = coincidencia.index ?? 0
    if (inicio > ultimo) nodos.push(texto.slice(ultimo, inicio))
    nodos.push(<strong key={inicio}>{coincidencia[1]}</strong>)
    ultimo = inicio + coincidencia[0].length
  }

  if (ultimo < texto.length) nodos.push(texto.slice(ultimo))
  return nodos
}

/**
 * Convierte el estado en un identificador seguro para clases CSS.
 *
 * El estado viaja como texto visible y, ademas, como clase: el color nunca es
 * el unico indicador del estado (RNF-01).
 */
function slug(estado: Estado): string {
  return estado
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z]+/g, '-')
}
