import { render, screen, waitFor } from '@testing-library/react'
import { beforeAll, describe, expect, it } from 'vitest'
import App from '../App'

/**
 * Prueba de integracion contra la API real: el frontend se monta sin mocks y
 * comprueba que el panel lateral carga el historial real.
 *
 * Se omite si la API no esta levantada (por ejemplo, en una ejecucion sin
 * servicios): para ejecutarla hay que levantar la API en el puerto 8000.
 */
const URL_API = process.env.WALLE_URL_API ?? 'http://127.0.0.1:8000'

async function apiDisponible(): Promise<boolean> {
  try {
    const respuesta = await fetch(`${URL_API}/api/salud`)
    return respuesta.ok
  } catch {
    return false
  }
}

describe('Integracion con la API real', () => {
  let disponible = false

  beforeAll(async () => {
    disponible = await apiDisponible()
  })

  it('el panel lateral carga el historial de la API', async () => {
    if (!disponible) {
      console.warn('API no disponible: se omite la prueba de integracion')
      return
    }

    render(<App />)

    await waitFor(
      async () => {
        const respuesta = await fetch(`${URL_API}/api/historial`)
        const historial = (await respuesta.json()) as { pregunta: string }[]
        if (historial.length > 0) {
          const primera = historial[0]
          expect(await screen.findByText(primera?.pregunta ?? '')).toBeInTheDocument()
        } else {
          expect(screen.getByText(/todavía no hay consultas/i)).toBeInTheDocument()
        }
      },
      { timeout: 8000 },
    )
  })
})
