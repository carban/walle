import { useCallback, useEffect, useRef, useState } from 'react'
import { borrarConsulta, consultar, obtenerConsulta, obtenerHistorial } from './api/cliente'
import { Aviso } from './componentes/Aviso'
import { Chat } from './componentes/Chat'
import { PanelHistorial } from './componentes/PanelHistorial'
import type { Intercambio, ResumenConsulta } from './tipos'
import { ErrorServidor, ErrorValidacion } from './tipos'

/** Ancho por debajo del cual el panel se superpone al chat (RNF-02). */
const ANCHO_ESTRECHO = '(max-width: 900px)'

/**
 * Composicion de la interfaz: panel lateral + chat.
 *
 * El estado vive aqui porque es el unico punto que coordina el cliente HTTP con
 * los dos paneles. El backend es la fuente de verdad del historial: el cliente
 * solo refleja lo que devuelve la API (R-03).
 */
export default function App() {
  const [intercambios, setIntercambios] = useState<Intercambio[]>([])
  const [historial, setHistorial] = useState<ResumenConsulta[]>([])
  const [enCurso, setEnCurso] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  // Contador para generar claves unicas: la misma entrada del historial puede
  // cargarse varias veces en el chat y React exige claves distintas.
  const contador = useRef(0)

  function nuevoId(prefijo: string): string {
    contador.current += 1
    return `${prefijo}-${contador.current}`
  }

  const refrescarHistorial = useCallback(async () => {
    try {
      setHistorial(await obtenerHistorial())
    } catch {
      // El historial es informativo: si falla, el chat sigue operativo.
    }
  }, [])

  useEffect(() => {
    // El historial se sincroniza con el servidor al montar: es una fuente externa.
    // oxlint-disable-next-line react/set-state-in-effect
    void refrescarHistorial()
  }, [refrescarHistorial])

  // En pantalla estrecha el panel se superpone al chat, asi que arranca cerrado
  // y se abre bajo demanda (RNF-02).
  const [estrecho, setEstrecho] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(ANCHO_ESTRECHO).matches,
  )
  const [panelVisible, setPanelVisible] = useState(() => {
    if (typeof window === 'undefined') return true
    return !window.matchMedia(ANCHO_ESTRECHO).matches
  })

  useEffect(() => {
    const consulta = window.matchMedia(ANCHO_ESTRECHO)
    function alCambiar(evento: MediaQueryListEvent) {
      setEstrecho(evento.matches)
      // Al pasar a estrecho se cierra el panel; al volver a ancho se muestra.
      setPanelVisible(!evento.matches)
    }
    consulta.addEventListener('change', alCambiar)
    return () => consulta.removeEventListener('change', alCambiar)
  }, [])

  async function enviar(pregunta: string) {
    const id = nuevoId('consulta')
    setIntercambios((previos) => [
      ...previos,
      { id, consultaId: null, pregunta, respuesta: null, enCurso: true },
    ])
    setEnCurso(true)
    setAviso(null)

    try {
      const respuesta = await consultar(pregunta)
      setIntercambios((previos) =>
        previos.map((intercambio) =>
          intercambio.id === id
            ? {
                ...intercambio,
                respuesta,
                consultaId: respuesta.consulta_id,
                enCurso: false,
              }
            : intercambio,
        ),
      )
    } catch (error) {
      // El error se muestra en el aviso; el intercambio en curso se retira para
      // no dejar una burbuja a medias, pero lo que ya estaba en pantalla se conserva.
      setIntercambios((previos) => previos.filter((intercambio) => intercambio.id !== id))
      if (error instanceof ErrorValidacion || error instanceof ErrorServidor) {
        setAviso(error.message)
      } else {
        setAviso('Ocurrió un error inesperado al realizar la consulta.')
      }
    } finally {
      setEnCurso(false)
      await refrescarHistorial()
    }
  }

  async function seleccionar(indice: number) {
    setAviso(null)
    try {
      const consulta = await obtenerConsulta(indice)
      setIntercambios((previos) => [
        ...previos,
        {
          id: nuevoId('historial'),
          consultaId: consulta.id,
          pregunta: consulta.pregunta,
          respuesta: {
            respuesta: consulta.respuesta,
            fuentes: consulta.fuentes,
            estado: consulta.estado,
            consulta_id: consulta.id,
            duracion_ms: consulta.duracion_ms,
            modelo: consulta.modelo,
          },
          enCurso: false,
        },
      ])
    } catch {
      setAviso('No se pudo recuperar la consulta del historial.')
    }
  }

  async function borrar(indice: number) {
    setAviso(null)
    try {
      await borrarConsulta(indice)
      // Actualizacion optimista: la entrada desaparece de inmediato y despues se
      // reconcilia con el servidor al refrescar el historial.
      setHistorial((previos) => previos.filter((consulta) => consulta.id !== indice))
      setIntercambios((previos) =>
        previos.filter((intercambio) => intercambio.consultaId !== indice),
      )
      await refrescarHistorial()
    } catch {
      setAviso('No se pudo borrar la consulta del historial.')
      await refrescarHistorial()
    }
  }

  function nuevaConversacion() {
    // Limpia el chat visible sin tocar el historial persistido (RF-04).
    setIntercambios([])
    setAviso(null)
  }

  return (
    <div
      className={`aplicacion ${panelVisible ? '' : 'aplicacion--sin-panel'} ${
        estrecho ? 'aplicacion--estrecho' : ''
      }`}
    >
      <PanelHistorial
        historial={historial}
        visible={panelVisible}
        onSeleccionar={(indice) => void seleccionar(indice)}
        onBorrar={(indice) => void borrar(indice)}
        onNueva={nuevaConversacion}
        onAlternar={() => setPanelVisible((visible) => !visible)}
      />

      <main className="principal">
        <div className="barra">
          <button
            type="button"
            className="boton boton--icono"
            onClick={() => setPanelVisible((visible) => !visible)}
            aria-label={panelVisible ? 'Ocultar historial' : 'Mostrar historial'}
            aria-expanded={panelVisible}
          >
            {panelVisible ? '‹' : '›'}
          </button>
        </div>

        {aviso ? <Aviso mensaje={aviso} /> : null}
        <Chat intercambios={intercambios} enCurso={enCurso} onEnviar={(p) => void enviar(p)} />
      </main>
    </div>
  )
}
