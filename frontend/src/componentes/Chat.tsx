import { useEffect, useRef } from 'react'
import type { Intercambio as IntercambioTipo } from '../tipos'
import { Intercambio } from './Intercambio'

interface Props {
  intercambios: IntercambioTipo[]
  enCurso: boolean
  onEnviar: (pregunta: string) => void
}

/** Area de conversacion: intercambios, estado de carga y campo de consulta. */
export function Chat({ intercambios, enCurso, onEnviar }: Props) {
  const campoRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!enCurso) campoRef.current?.focus()
  }, [enCurso])

  function enviar() {
    const pregunta = campoRef.current?.value.trim() ?? ''
    if (!pregunta || enCurso) return
    onEnviar(pregunta)
    if (campoRef.current) campoRef.current.value = ''
  }

  function alPulsarTecla(evento: React.KeyboardEvent<HTMLTextAreaElement>) {
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
          onKeyDown={alPulsarTecla}
          disabled={enCurso}
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
