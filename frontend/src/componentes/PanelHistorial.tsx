import type { ConsultaHistorial } from '../tipos'

interface Props {
  historial: ConsultaHistorial[]
  visible: boolean
  onSeleccionar: (indice: number) => void
  onBorrar: (indice: number) => void
  onNueva: () => void
  onAlternar: () => void
}

/** Panel lateral con las consultas anteriores. */
export function PanelHistorial({
  historial,
  visible,
  onSeleccionar,
  onBorrar,
  onNueva,
  onAlternar,
}: Props) {
  return (
    <aside className={`panel ${visible ? 'panel--visible' : 'panel--oculto'}`} aria-label="Historial">
      <header className="panel__cabecera">
        <h2 className="panel__titulo">Walle</h2>
        <button
          type="button"
          className="boton boton--icono"
          onClick={onAlternar}
          aria-label={visible ? 'Ocultar historial' : 'Mostrar historial'}
        >
          {visible ? '‹' : '›'}
        </button>
      </header>

      <button type="button" className="boton boton--secundario panel__nueva" onClick={onNueva}>
        Nueva conversación
      </button>

      <nav className="panel__lista" aria-label="Consultas anteriores">
        {historial.length === 0 ? (
          <p className="panel__vacio">Todavía no hay consultas registradas.</p>
        ) : (
          <ul>
            {historial.map((consulta) => (
              <li key={consulta.id} className="panel__item">
                <button
                  type="button"
                  className="panel__consulta"
                  onClick={() => onSeleccionar(consulta.id)}
                >
                  <span className="panel__pregunta">{consulta.pregunta}</span>
                  <span className="panel__meta">
                    {formatearFecha(consulta.fecha_hora)} · {consulta.estado}
                  </span>
                </button>
                <button
                  type="button"
                  className="boton boton--icono"
                  onClick={() => onBorrar(consulta.id)}
                  aria-label={`Borrar la consulta: ${consulta.pregunta}`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </nav>
    </aside>
  )
}

function formatearFecha(fechaIso: string): string {
  const fecha = new Date(fechaIso)
  if (Number.isNaN(fecha.getTime())) return fechaIso
  return fecha.toLocaleString('es-CO', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
