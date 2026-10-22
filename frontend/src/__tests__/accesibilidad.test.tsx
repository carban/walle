/**
 * Pruebas de accesibilidad basica (RNF-01).
 *
 * Los controles tienen etiqueta asociada, el error se anuncia con `aria-live`
 * y los estados se distinguen tambien por texto, no solo por color.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { consultar, obtenerHistorial } from '../api/cliente'
import { ErrorServidor } from '../tipos'

vi.mock('../api/cliente', () => ({
  consultar: vi.fn(),
  obtenerHistorial: vi.fn(),
  obtenerConsulta: vi.fn(),
  borrarConsulta: vi.fn(),
}))

describe('Accesibilidad de la interfaz', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(obtenerHistorial).mockResolvedValue([])
    vi.mocked(consultar).mockResolvedValue({
      respuesta: 'El monto máximo es $50.000.000.',
      fuentes: [{ documento: 'Productos de Crédito.md', fragmento: 'Condiciones' }],
      estado: 'Exitosa',
      consulta_id: 1,
      duracion_ms: 1200,
      modelo: 'minimax/minimax-m3.1-flash:free',
    })
  })

  it('el campo de consulta tiene etiqueta asociada', () => {
    render(<App />)

    const campo = screen.getByRole('textbox', { name: /tu consulta/i })
    expect(campo).toBeInTheDocument()
    expect(campo).toHaveAccessibleName('Tu consulta')
  })

  it('el panel lateral tiene nombre accesible', async () => {
    render(<App />)

    expect(await screen.findByRole('complementary', { name: /historial/i })).toBeInTheDocument()
  })

  it('el aviso de error se anuncia con una región aria-live', async () => {
    vi.mocked(consultar).mockRejectedValue(new ErrorServidor('No se pudo completar la consulta.'))
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.type(screen.getByRole('textbox', { name: /tu consulta/i }), 'consulta')
    await usuario.click(screen.getByRole('button', { name: /^enviar$/i }))

    const aviso = await screen.findByRole('alert')
    expect(aviso).toHaveAttribute('aria-live', 'assertive')
    expect(aviso).toHaveTextContent('No se pudo completar la consulta.')
  })

  it('los estados se distinguen por texto, no solo por color', async () => {
    vi.mocked(consultar).mockResolvedValue({
      respuesta: 'No tengo información suficiente para responder.',
      fuentes: [],
      estado: 'Sin información suficiente',
      consulta_id: 2,
      duracion_ms: 10,
      modelo: '',
    })
    const usuario = userEvent.setup()
    render(<App />)

    await usuario.type(screen.getByRole('textbox', { name: /tu consulta/i }), 'consulta')
    await usuario.click(screen.getByRole('button', { name: /^enviar$/i }))

    // El texto del estado es legible por si mismo: no depende del color.
    const etiqueta = await screen.findByText('Sin información suficiente')
    expect(etiqueta).toBeVisible()
    expect(etiqueta).toHaveTextContent('Sin información suficiente')
  })

  it('se puede enviar la consulta solo con el teclado', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    // Solo con tabulador: se llega al campo pulsando repetidamente.
    const campo = screen.getByRole('textbox', { name: /tu consulta/i })
    for (let intento = 0; intento < 10 && document.activeElement !== campo; intento += 1) {
      await usuario.tab()
    }
    expect(document.activeElement).toBe(campo)

    await usuario.keyboard('monto máximo{Enter}')

    await waitFor(() => expect(consultar).toHaveBeenCalledWith('monto máximo'))
  })

  it('el foco vuelve al campo de consulta al terminar (RNF-01)', async () => {
    const usuario = userEvent.setup()
    render(<App />)

    const campo = screen.getByRole('textbox', { name: /tu consulta/i })
    await usuario.click(campo)
    await usuario.type(campo, 'monto máximo')
    await usuario.click(screen.getByRole('button', { name: /^enviar$/i }))

    await waitFor(() => expect(campo).toHaveFocus())
  })

  it('el botón de enviar es alcanzable y tiene nombre accesible', () => {
    render(<App />)

    expect(screen.getByRole('button', { name: /^enviar$/i })).toBeInTheDocument()
  })

  it('la conversación se anuncia con aria-live', () => {
    render(<App />)

    const conversacion = screen.getByRole('region', { name: /conversación/i })
    expect(conversacion).toBeInTheDocument()
    expect(conversacion.querySelector('[aria-live="polite"]')).toBeTruthy()
  })
})
