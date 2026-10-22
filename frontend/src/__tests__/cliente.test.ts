/**
 * Pruebas del cliente HTTP: URL, metodo, cuerpo y traduccion de errores (T-206, T-207).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  borrarConsulta,
  consultar,
  obtenerConsulta,
  obtenerHistorial,
} from '../api/cliente'
import { ErrorServidor, ErrorValidacion } from '../tipos'

const API = 'http://127.0.0.1:8000'

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('Cliente HTTP de la API', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('consulta apuntando a la API del puerto 8000', async () => {
    const cuerpo = {
      respuesta: 'El monto máximo es $50.000.000.',
      fuentes: [{ documento: 'Productos de Crédito.md', fragmento: 'Condiciones' }],
      estado: 'Exitosa',
      consulta_id: 1,
      duracion_ms: 900,
      modelo: 'minimax/minimax-m3.1-flash:free',
    }
    vi.mocked(fetch).mockResolvedValue(respuestaJson(cuerpo))

    const resultado = await consultar('¿monto máximo?')

    expect(resultado.respuesta).toBe('El monto máximo es $50.000.000.')
    expect(fetch).toHaveBeenCalledTimes(1)

    const [url, opciones] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${API}/api/consultar`)
    expect(opciones.method).toBe('POST')
    expect(JSON.parse(String(opciones.body))).toEqual({ pregunta: '¿monto máximo?' })
  })

  it('envia las cabeceras de JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(respuestaJson({ respuesta: '', fuentes: [], estado: 'Exitosa', consulta_id: null, duracion_ms: 0, modelo: '' }))

    await consultar('hola')

    const [, opciones] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(opciones.headers).toMatchObject({
      'Content-Type': 'application/json',
      Accept: 'application/json',
    })
  })

  it('lista el historial con el recurso paginado', async () => {
    vi.mocked(fetch).mockResolvedValue(respuestaJson([]))

    await obtenerHistorial()

    const [url] = vi.mocked(fetch).mock.calls[0] as [string]
    expect(url).toBe(`${API}/api/consultas?limite=200&desplazamiento=0`)
  })

  it('pide el detalle de una consulta por indice', async () => {
    vi.mocked(fetch).mockResolvedValue(respuestaJson({ id: 7 }))

    await obtenerConsulta(7)

    const [url, opciones] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${API}/api/consultas/7`)
    expect(opciones.method).toBeUndefined()
  })

  it('borra una consulta por indice', async () => {
    vi.mocked(fetch).mockResolvedValue(respuestaJson({ eliminado: true, indice: 7 }))

    const resultado = await borrarConsulta(7)

    expect(resultado.eliminado).toBe(true)
    const [url, opciones] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${API}/api/consultas/7`)
    expect(opciones.method).toBe('DELETE')
  })

  it('traduce un 422 en ErrorValidacion con el mensaje del servidor', async () => {
    // Cada llamada necesita su propia Response: el cuerpo se consume al leerlo.
    vi.mocked(fetch).mockImplementation(async () =>
      respuestaJson(
        {
          detail: [
            {
              loc: ['body', 'pregunta'],
              msg: 'String should have at least 3 characters',
              type: 'string_too_short',
            },
          ],
        },
        422,
      ),
    )

    await expect(consultar('ab')).rejects.toBeInstanceOf(ErrorValidacion)
    await expect(consultar('ab')).rejects.toThrow(/pregunta/)
  })

  it('traduce un 422 con detalle en texto plano', async () => {
    vi.mocked(fetch).mockImplementation(async () => respuestaJson({ detail: 'pregunta no valida' }, 422))

    await expect(consultar('ab')).rejects.toThrow('pregunta no valida')
  })

  it('traduce un 500 en ErrorServidor sin filtrar detalles internos', async () => {
    vi.mocked(fetch).mockResolvedValue(
      respuestaJson({ detail: 'Traceback (most recent call last): ...' }, 500),
    )

    const error = await consultar('hola').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ErrorServidor)
    expect((error as Error).message).not.toMatch(/Traceback/)
  })

  it('traduce un 502 del proxy en ErrorServidor', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('', { status: 502 }))

    await expect(consultar('hola')).rejects.toBeInstanceOf(ErrorServidor)
  })

  it('traduce un fallo de red en ErrorServidor con un mensaje accionable', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await consultar('hola').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ErrorServidor)
    expect((error as Error).message).toMatch(/8000/)
  })

  it('no incluye la traza ni el stack en el mensaje de error', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('boom'))

    const error = await consultar('hola').catch((e: unknown) => e)

    expect((error as Error).message).not.toMatch(/boom/)
    expect((error as Error).message).not.toMatch(/at .*\.ts/)
  })
})
