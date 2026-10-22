import { useEffect, useRef, useState } from 'react'
import type { Intercambio as IntercambioTipo } from '../tipos'
import { Intercambio } from './Intercambio'

interface Props {
  intercambios: IntercambioTipo[]
  enCurso: boolean
  onEnviar: (pregunta: string) => void
}

/**
 * Area de conversacion: intercambios, estado de carga y campo de consulta (RF-01).
 *
 * El campo es controlado por React para que el envio vacie el valor de forma
 * consistente y para que el texto sobreviva a un fallo de red.
 */
export function Chat({ intercambios, enCurso, onEnviar }: Props) {
  const [pregunta, setPregunta] = useState('')
  const campoRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    // Al terminar la consulta el foco vuelve al campo para seguir escribiendo.
    if (!enCurso) campoRef.current?.focus()
  }, [enCurso])

  function enviar() {
    const texto = pregunta.trim()
    // Una pregunta vacia no llega al servidor (RF-01).
    if (!texto || enCurso) return
    onEnviar(texto)
    setPregunta('')
  }

  function alPulsarTecla(evento: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter envia; Shift+Enter inserta un salto de linea.
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault()
      enviar()
    }
  }

  return (
    <section className="chat" aria-label="Conversación">
      <div className="chat__mensajes" aria-live="polite">
        {intercambios.length === 0 && !enCurso ? (
          <div className="chat__vacio">
            <h2>¿En qué puedo ayudarte?</h2>
            <p>
              Consulta sobre productos de crédito, microseguros, procedimientos operativos y
              políticas internas. Las respuestas siempre citan su fuente.
            </p>
          </div>
        ) : null}

        {intercambios.map((intercambio) =>
          intercambio.respuesta ? (
            <Intercambio
              key={intercambio.id}
              pregunta={intercambio.pregunta}
              respuesta={intercambio.respuesta.respuesta}
              estado={intercambio.respuesta.estado}
              fuentes={intercambio.respuesta.fuentes}
              duracionMs={intercambio.respuesta.duracion_ms}
              modelo={intercambio.respuesta.modelo}
            />
          ) : (
            <article className="intercambio" key={intercambio.id}>
              <div className="burbuja burbuja--usuario">
                <p className="burbuja__texto">{intercambio.pregunta}</p>
              </div>
              <div className="burbuja burbuja--asistente burbuja--carga" aria-label="Consultando">
                <span className="spinner" aria-hidden="true" />
                <span>Consultando…</span>
              </div>
            </article>
          ),
        )}
      </div>

      <div className="compositor">
        <label className="compositor__etiqueta" htmlFor="campo-pregunta">
          Tu consulta
        </label>
        <textarea
          id="campo-pregunta"
          ref={campoRef}
          className="compositor__campo"
          placeholder="Escribe tu consulta…"
          rows={2}
          value={pregunta}
          onChange={(evento) => setPregunta(evento.target.value)}
          onKeyDown={alPulsarTecla}
        />
        <button
          type="button"
          className="boton boton--primario"
          onClick={enviar}
          disabled={enCurso}
        >
          {enCurso ? 'Consultando…' : 'Enviar'}
        </button>
      </div>
    </section>
  )
}
