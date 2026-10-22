import { useCallback, useEffect, useState } from 'react'
import { borrarConsulta, consultar, obtenerConsulta, obtenerHistorial } from './api/cliente'
import { Aviso } from './componentes/Aviso'
import { Chat } from './componentes/Chat'
import { PanelHistorial } from './componentes/PanelHistorial'
import type { ConsultaHistorial, Intercambio } from './tipos'
import { ErrorServidor, ErrorValidacion } from './tipos'

export default function App() {
  const [intercambios, setIntercambios] = useState<Intercambio[]>([])
  const [historial, setHistorial] = useState<ConsultaHistorial[]>([])
  const [enCurso, setEnCurso] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const [panelVisible, setPanelVisible] = useState(true)

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

  async function enviar(pregunta: string) {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
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
          intercambio.id === id ? { ...intercambio, respuesta, enCurso: false } : intercambio,
        ),
      )
    } catch (error) {
      setIntercambios((previos) => previos.filter((intercambio) => intercambio.id !== id))
      if (error instanceof ErrorValidacion) {
        setAviso(error.message)
      } else if (error instanceof ErrorServidor) {
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
          id: `historial-${consulta.id}`,
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
      setIntercambios((previos) =>
        previos.filter((intercambio) => intercambio.consultaId !== indice),
      )
      await refrescarHistorial()
    } catch {
      setAviso('No se pudo borrar la consulta del historial.')
    }
  }

  function nuevaConversacion() {
    setIntercambios([])
    setAviso(null)
  }

  return (
    <div className={`aplicacion ${panelVisible ? '' : 'aplicacion--sin-panel'}`}>
      <PanelHistorial
        historial={historial}
        visible={panelVisible}
        onSeleccionar={(indice) => void seleccionar(indice)}
        onBorrar={(indice) => void borrar(indice)}
        onNueva={nuevaConversacion}
        onAlternar={() => setPanelVisible((visible) => !visible)}
      />

      <main className="principal">
        {aviso ? <Aviso mensaje={aviso} /> : null}
        <Chat intercambios={intercambios} enCurso={enCurso} onEnviar={(p) => void enviar(p)} />
      </main>
    </div>
  )
}
