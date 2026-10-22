import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { borrarConsulta, consultar, obtenerConsulta, obtenerHistorial } from '../api/cliente'
import { ErrorServidor, ErrorValidacion } from '../tipos'
import type { ConsultaHistorial, ConsultaResponse } from '../tipos'

vi.mock('../api/cliente', () => ({
  consultar: vi.fn(),
  obtenerHistorial: vi.fn(),
  obtenerConsulta: vi.fn(),
  borrarConsulta: vi.fn(),
}))

const respuestaExitosa: ConsultaResponse = {
  respuesta: 'El monto máximo es $50.000.000.',
  fuentes: [{ documento: 'Productos de Crédito.md', fragmento: 'Crédito Productivo Impulso' }],
  estado: 'Exitosa',
  consulta_id: 1,
  duracion_ms: 1200,
  modelo: 'minimax/minimax-m3.1-flash:free',
}

const consultaPrevia: ConsultaHistorial = {
  id: 1,
  pregunta: '¿Cuál es el monto máximo del Crédito Productivo Impulso?',
  fecha_hora: '2026-10-21T10:00:00+00:00',
  respuesta: 'El monto máximo es $50.000.000.',
  fuentes: [{ documento: 'Productos de Crédito.md', fragmento: 'Condiciones' }],
  estado: 'Exitosa',
  duracion_ms: 900,
  modelo: 'minimax/minimax-m3.1-flash:free',
}

const historial: ConsultaHistorial[] = [
  {
    id: 1,
    pregunta: '¿Cuál es el monto máximo del Crédito Productivo Impulso?',
    fecha_hora: '2026-10-21T10:00:00+00:00',
    respuesta: 'El monto máximo es $50.000.000.',
    fuentes: [{ documento: 'Productos de Crédito.md', fragmento: 'Condiciones' }],
    estado: 'Exitosa',
    duracion_ms: 900,
    modelo: 'minimax/minimax-m3.1-flash:free',
  },
]

describe('Interfaz de consultas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(obtenerHistorial).mockResolvedValue([])
    vi.mocked(consultar).mockResolvedValue(respuestaExitosa)
    vi.mocked(obtenerConsulta).mockResolvedValue(consultaPrevia)
    vi.mocked(borrarConsulta).mockResolvedValue(undefined)
  })

  it('muestra el estado inicial', () => {
    render(<App />)

    expect(screen.getByText('¿En qué puedo ayudarte?')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /tu consulta/i })).toBeInTheDocument()
  })

  it('envía la consulta y muestra la respuesta con sus fuentes', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.type(screen.getByRole('textbox', { name: /tu consulta/i }), 'monto máximo')
    await usuario.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByText('El monto máximo es $50.000.000.')).toBeInTheDocument()
    })
    expect(consultar).toHaveBeenCalledWith('monto máximo')
    expect(screen.getByText('Exitosa')).toBeInTheDocument()
    expect(screen.getByText('Productos de Crédito.md')).toBeInTheDocument()
    expect(screen.getByText('Crédito Productivo Impulso')).toBeInTheDocument()
  })

  it('no envía una pregunta vacía', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(screen.getByRole('button', { name: /enviar/i }))

    expect(consultar).not.toHaveBeenCalled()
  })

  it('muestra el estado de procesamiento mientras espera la respuesta', async () => {
    let resolver: (valor: ConsultaResponse) => void = () => {}
    vi.mocked(consultar).mockReturnValue(
      new Promise<ConsultaResponse>((resolve) => {
        resolver = resolve
      }),
    )
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.type(screen.getByRole('textbox', { name: /tu consulta/i }), 'monto')
    await usuario.click(screen.getByRole('button', { name: /enviar/i }))

    expect((await screen.findAllByText('Consultando…')).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /consultando/i })).toBeDisabled()

    resolver(respuestaExitosa)
    await waitFor(() => {
      expect(screen.getByText('El monto máximo es $50.000.000.')).toBeInTheDocument()
    })
  })

  it('muestra un aviso cuando la API rechaza la pregunta', async () => {
    vi.mocked(consultar).mockRejectedValue(
      new ErrorValidacion('El campo "pregunta" debe tener al menos 3 caracteres.'),
    )
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.type(screen.getByRole('textbox', { name: /tu consulta/i }), 'ab')
    await usuario.click(screen.getByRole('button', { name: /enviar/i }))

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('pregunta')
  })

  it('muestra un aviso cuando no hay conexión con la API', async () => {
    vi.mocked(consultar).mockRejectedValue(
      new ErrorServidor('No se pudo conectar con el servidor.'),
    )
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.type(screen.getByRole('textbox', { name: /tu consulta/i }), 'monto')
    await usuario.click(screen.getByRole('button', { name: /enviar/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar')
  })

  it('trata "sin información suficiente" como respuesta y no como error', async () => {
    vi.mocked(consultar).mockResolvedValue({
      respuesta: 'No tengo información suficiente para responder.',
      fuentes: [],
      estado: 'Sin información suficiente',
      consulta_id: 2,
      duracion_ms: 3,
      modelo: '',
    })
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.type(screen.getByRole('textbox', { name: /tu consulta/i }), 'clima')
    await usuario.click(screen.getByRole('button', { name: /enviar/i }))

    expect(
      await screen.findByText('No tengo información suficiente para responder.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Sin información suficiente')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('muestra las consultas anteriores en el panel lateral', async () => {
    vi.mocked(obtenerHistorial).mockResolvedValue(historial)
    render(<App />)

    expect(await screen.findByText(consultaPrevia.pregunta)).toBeInTheDocument()
  })

  it('carga en el chat la consulta seleccionada del historial', async () => {
    vi.mocked(obtenerHistorial).mockResolvedValue(historial)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(await screen.findByText(consultaPrevia.pregunta))

    await waitFor(() => {
      expect(obtenerConsulta).toHaveBeenCalledWith(1)
    })
    expect(await screen.findByText('El monto máximo es $50.000.000.')).toBeInTheDocument()
  })

  it('borra una consulta del historial tras confirmar', async () => {
    vi.mocked(obtenerHistorial).mockResolvedValue(historial)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(await screen.findByRole('button', { name: /borrar la consulta/i }))
    await usuario.click(screen.getByRole('button', { name: /confirmar el borrado/i }))

    await waitFor(() => {
      expect(borrarConsulta).toHaveBeenCalledWith(1)
    })
  })

  it('el borrado se puede cancelar', async () => {
    vi.mocked(obtenerHistorial).mockResolvedValue(historial)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(await screen.findByRole('button', { name: /borrar la consulta/i }))
    await usuario.click(screen.getByRole('button', { name: /cancelar el borrado/i }))

    expect(borrarConsulta).not.toHaveBeenCalled()
    expect(screen.getByText(consultaPrevia.pregunta)).toBeInTheDocument()
  })

  it('cargar dos veces la misma entrada del historial no rompe el chat', async () => {
    vi.mocked(obtenerHistorial).mockResolvedValue(historial)
    const usuario = userEvent.setup()
    render(<App />)

    const entrada = await screen.findByText(consultaPrevia.pregunta)
    await usuario.click(entrada)
    await usuario.click(entrada)

    await waitFor(() => {
      expect(obtenerConsulta).toHaveBeenCalledTimes(2)
    })
    // Ambas cargas se muestran y no se duplican claves de React.
    expect(await screen.findAllByText('El monto máximo es $50.000.000.')).toHaveLength(2)
  })

  it('la nueva conversación limpia el chat y conserva el historial', async () => {
    vi.mocked(obtenerHistorial).mockResolvedValue(historial)
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.click(await screen.findByText(consultaPrevia.pregunta))
    await waitFor(() => {
      expect(screen.getByText('El monto máximo es $50.000.000.')).toBeInTheDocument()
    })

    await usuario.click(screen.getByRole('button', { name: /nueva conversación/i }))

    expect(screen.queryByText('El monto máximo es $50.000.000.')).not.toBeInTheDocument()
    expect(screen.getByText(consultaPrevia.pregunta)).toBeInTheDocument()
  })
})
