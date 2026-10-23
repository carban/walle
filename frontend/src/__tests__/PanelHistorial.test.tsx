/**
 * Pruebas del panel lateral: listado, seleccion, borrado y nueva conversacion.
 *
 * Trazabilidad: RF-04, RNF-02.
 */

import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { borrarConsulta, obtenerConsulta, obtenerHistorial } from '../api/cliente'
import { ErrorServidor } from '../tipos'
import type { ResumenConsulta } from '../tipos'

vi.mock('../api/cliente', () => ({
  consultar: vi.fn(),
  obtenerHistorial: vi.fn(),
  obtenerConsulta: vi.fn(),
  borrarConsulta: vi.fn(),
}))

function consulta(indice: number, pregunta: string): ResumenConsulta {
  return {
    id: indice,
    pregunta,
    fecha_hora: `2026-10-2${indice}T10:00:00+00:00`,
    respuesta: 'El monto máximo es $50.000.000.',
    fuentes: [{ documento: 'Productos de Crédito.md', fragmento: 'Condiciones' }],
    estado: 'Exitosa',
    duracion_ms: 900,
    modelo: 'cohere/north-mini-code:free',
  }
}

const historial: ResumenConsulta[] = [
  consulta(3, 'tercera consulta'),
  consulta(2, 'segunda consulta'),
  consulta(1, 'primera consulta'),
]

describe('Panel lateral con el historial', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(obtenerHistorial).mockResolvedValue(historial)
    vi.mocked(obtenerConsulta).mockResolvedValue(historial[0] as ResumenConsulta)
    vi.mocked(borrarConsulta).mockResolvedValue({ eliminado: true, indice: 1 })
  })

  it('muestra las consultas del historial al montar (RF-04)', async () => {
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    const entradas = within(panel).getAllByRole('listitem')

    expect(entradas).toHaveLength(3)
    expect(within(panel).getByText('tercera consulta')).toBeInTheDocument()
    expect(within(panel).getByText('primera consulta')).toBeInTheDocument()
  })

  it('muestra las entradas de la más reciente a la más antigua (RF-04)', async () => {
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    const preguntas = within(panel)
      .getAllByRole('listitem')
      .map((item) => item.textContent ?? '')

    expect(preguntas[0]).toContain('tercera consulta')
    expect(preguntas[2]).toContain('primera consulta')
  })

  it('muestra la fecha, la hora y el estado de cada entrada (RF-04)', async () => {
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    const entrada = within(panel).getAllByRole('listitem')[0]

    expect(entrada).toHaveTextContent(/\d{2}\/\d{2}/)
    expect(entrada).toHaveTextContent(/\d{2}:\d{2}/)
    expect(entrada).toHaveTextContent('Exitosa')
  })

  it('carga el detalle de la consulta seleccionada en el chat (RF-04)', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await usuario.click(within(panel).getByText('tercera consulta'))

    await waitFor(() => expect(obtenerConsulta).toHaveBeenCalledWith(3))
    expect(await screen.findByText('El monto máximo es $50.000.000.')).toBeInTheDocument()
    expect(screen.getByText('Productos de Crédito.md')).toBeInTheDocument()
  })

  it('mantiene el resto de las entradas tras seleccionar una (RF-04)', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await usuario.click(within(panel).getByText('tercera consulta'))

    await waitFor(() => expect(obtenerConsulta).toHaveBeenCalled())
    expect(within(panel).getAllByRole('listitem')).toHaveLength(3)
  })

  it('borra la consulta seleccionada tras la confirmación (RF-04)', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await usuario.click(within(panel).getByRole('button', { name: /borrar la consulta: primera/i }))

    // La confirmacion aparece antes de borrar nada.
    expect(borrarConsulta).not.toHaveBeenCalled()

    // A partir de aqui el servidor ya no devuelve la consulta borrada.
    vi.mocked(obtenerHistorial).mockImplementation(async () =>
      historial.filter((entrada) => entrada.id !== 1),
    )
    await usuario.click(screen.getByRole('button', { name: /confirmar el borrado/i }))

    await waitFor(() => expect(borrarConsulta).toHaveBeenCalledWith(1))
    await waitFor(() => {
      expect(within(panel).queryByText('primera consulta')).not.toBeInTheDocument()
    })
  })

  it('no borra nada si se cancela la confirmación (RF-04)', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await usuario.click(within(panel).getByRole('button', { name: /borrar la consulta: primera/i }))
    await usuario.click(screen.getByRole('button', { name: /cancelar el borrado/i }))

    expect(borrarConsulta).not.toHaveBeenCalled()
    expect(within(panel).getByText('primera consulta')).toBeInTheDocument()
  })

  it('reconcilia con el servidor tras el borrado (RF-04)', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await waitFor(() => expect(obtenerHistorial).toHaveBeenCalledTimes(1))

    await usuario.click(within(panel).getByRole('button', { name: /borrar la consulta: primera/i }))
    await usuario.click(screen.getByRole('button', { name: /confirmar el borrado/i }))

    await waitFor(() => expect(obtenerHistorial).toHaveBeenCalledTimes(2))
  })

  it('muestra un aviso si el borrado falla (RF-05)', async () => {
    vi.mocked(borrarConsulta).mockRejectedValue(new ErrorServidor('No se pudo borrar.'))
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await usuario.click(within(panel).getByRole('button', { name: /borrar la consulta: primera/i }))
    await usuario.click(screen.getByRole('button', { name: /confirmar el borrado/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/no se pudo borrar/i)
  })

  it('limpia el chat sin tocar el historial con "Nueva pregunta" (RF-04)', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await usuario.click(within(panel).getByText('tercera consulta'))
    await screen.findByText('El monto máximo es $50.000.000.')

    await usuario.click(screen.getByRole('button', { name: /nueva pregunta/i }))

    expect(screen.queryByText('El monto máximo es $50.000.000.')).not.toBeInTheDocument()
    expect(screen.getByText(/¿En qué puedo ayudarte\?/)).toBeInTheDocument()
    expect(within(panel).getAllByRole('listitem')).toHaveLength(3)
  })

  it('muestra un aviso si no se puede recuperar una consulta del historial (RF-05)', async () => {
    vi.mocked(obtenerConsulta).mockRejectedValue(new ErrorServidor('No se pudo recuperar.'))
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await usuario.click(within(panel).getByText('tercera consulta'))

    expect(await screen.findByRole('alert')).toHaveTextContent(/no se pudo recuperar/i)
  })

  it('oculta y muestra el panel lateral sin perder la conversación (RNF-02)', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    const panel = await screen.findByRole('complementary', { name: /historial/i })
    await usuario.click(within(panel).getByText('tercera consulta'))
    await screen.findByText('El monto máximo es $50.000.000.')

    await usuario.click(screen.getByRole('button', { name: /ocultar historial/i }))
    expect(panel).not.toBeVisible()

    // El contenido del chat sigue presente con el panel oculto.
    expect(screen.getByText('El monto máximo es $50.000.000.')).toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: /mostrar historial/i }))
    expect(panel).toBeVisible()
    expect(screen.getByText('El monto máximo es $50.000.000.')).toBeInTheDocument()
  })

  it('arranca con el panel oculto en pantalla estrecha (RNF-02)', async () => {
    // Se simula una ventana estrecha antes de montar.
    vi.spyOn(window, 'matchMedia').mockImplementation((consulta: string) => ({
      matches: true,
      media: consulta,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }))

    render(<App />)

    expect(screen.queryByRole('complementary', { name: /historial/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /mostrar historial/i })).toBeInTheDocument()
  })
})
