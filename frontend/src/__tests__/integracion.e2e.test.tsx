/**
 * Prueba de integracion contra la API real (puerto 8000).
 *
 * El frontend se monta sin mocks y comprueba que el panel lateral carga el
 * historial real del backend. Se omite si la API no esta levantada: para
 * ejecutarla hay que levantar la API con
 * `uv run uvicorn walle.main:app --port 8000`.
 */

import { render, screen, waitFor } from '@testing-library/react'
import { beforeAll, describe, expect, it } from 'vitest'
import App from '../App'

const URL_API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function apiDisponible(): Promise<boolean> {
  try {
    const respuesta = await fetch(`${URL_API}/health`)
    return respuesta.ok
  } catch {
    return false
  }
}

async function historialReal(): Promise<{ pregunta: string }[]> {
  const respuesta = await fetch(`${URL_API}/api/consultas?limite=200&desplazamiento=0`)
  return (await respuesta.json()) as { pregunta: string }[]
}

describe('Integracion con la API real', () => {
  let disponible = false

  beforeAll(async () => {
    disponible = await apiDisponible()
  })

  it('el panel lateral carga el historial de la API', async () => {
    if (!disponible) {
      console.warn(`API no disponible en ${URL_API}: se omite la prueba de integracion`)
      return
    }

    const historial = await historialReal()
    render(<App />)

    await waitFor(
      async () => {
        const panel = screen.getByRole('complementary', { name: /historial/i })
        const entradas = panel.querySelectorAll('li')
        if (historial.length > 0) {
          // La pregunta mas reciente aparece en el panel, junto a su fecha y estado.
          const masReciente = historial[0]?.pregunta ?? ''
          expect(entradas.length).toBeGreaterThan(0)
          expect(panel.textContent).toContain(masReciente)
          expect(panel.textContent).toContain('Exitosa')
        } else {
          expect(panel.textContent).toMatch(/todavía no hay consultas/i)
        }
      },
      { timeout: 10000 },
    )
  }, 20000)
})
