import { useState } from 'react'
import type { ResumenConsulta } from '../tipos'

interface Props {
  historial: ResumenConsulta[]
  visible: boolean
  onSeleccionar: (indice: number) => void
  onBorrar: (indice: number) => void
  onNueva: () => void
  onAlternar: () => void
}

/**
 * Panel lateral con las consultas anteriores (RF-04).
 *
 * El borrado pide confirmacion en linea para que una consulta no se pierda por
 * un clic accidental: primero se muestra la confirmacion y despues se borra.
 *
 * El panel lleva su propio boton de cierre: en pantalla estrecha se superpone
 * al chat y taparia el boton de la barra principal.
 */
export function PanelHistorial({
  historial,
  visible,
  onSeleccionar,
  onBorrar,
  onNueva,
  onAlternar,
}: Props) {
  // Indice de la entrada que espera confirmacion de borrado.
  const [pendiente, setPendiente] = useState<number | null>(null)

  function confirmarBorrado(indice: number) {
    setPendiente(null)
    onBorrar(indice)
  }

  function alPulsarTecla(evento: React.KeyboardEvent<HTMLLIElement>, indice: number) {
    if (evento.key === 'Escape' && pendiente === indice) {
      setPendiente(null)
    }
  }

  return (
    <aside
      className={`panel ${visible ? 'panel--visible' : 'panel--oculto'}`}
      aria-label="Historial"
      hidden={!visible}
    >
      <header className="panel__cabecera">
        <h2 className="panel__titulo">Walle</h2>
        <button
          type="button"
          className="boton boton--icono panel__cerrar"
          onClick={onAlternar}
          aria-label="Cerrar historial"
        >
          ‹
        </button>
      </header>

      <button type="button" className="boton boton--secundario panel__nueva" onClick={onNueva}>
        Nueva pregunta
      </button>

      <nav className="panel__lista" aria-label="Consultas anteriores">
        {historial.length === 0 ? (
          <p className="panel__vacio">Todavía no hay consultas registradas.</p>
        ) : (
          <ul>
            {historial.map((consulta) => {
              const enConfirmacion = pendiente === consulta.id
              return (
                <li
                  key={consulta.id}
                  className="panel__item"
                  onKeyDown={(evento) => alPulsarTecla(evento, consulta.id)}
                >
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

                  {enConfirmacion ? (
                    <div className="panel__confirmacion">
                      <span className="panel__confirmacion-texto">¿Eliminar?</span>
                      <button
                        type="button"
                        className="boton boton--peligro"
                        onClick={() => confirmarBorrado(consulta.id)}
                        aria-label={`Confirmar el borrado de la consulta: ${consulta.pregunta}`}
                        autoFocus
                      >
                        Sí
                      </button>
                      <button
                        type="button"
                        className="boton boton--secundario"
                        onClick={() => setPendiente(null)}
                        aria-label="Cancelar el borrado"
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="boton boton--borrar"
                      onClick={() => setPendiente(consulta.id)}
                      aria-label={`Borrar la consulta: ${consulta.pregunta}`}
                      title="Eliminar del historial"
                    >
                      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                        <path
                          fill="currentColor"
                          d="M9 3h6l1 2h4v2H4V5h4l1-2Zm-3 6h12l-1 12H7L6 9Zm3 2v8h2v-8H9Zm4 0v8h2v-8h-2Z"
                        />
                      </svg>
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </nav>
    </aside>
  )
}

/** Formatea la fecha ISO de la API en formato local legible. */
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
