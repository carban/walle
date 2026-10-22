import { beforeEach, describe, expect, it, vi } from 'vitest'
import { borrarConsulta, consultar, obtenerHistorial } from '../api/cliente'
import { ErrorServidor, ErrorValidacion } from '../tipos'

function respuestaJson(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('Cliente HTTP de la API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('consulta al backend y devuelve la respuesta', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      respuestaJson({
        respuesta: 'ok',
        fuentes: [],
        estado: 'Exitosa',
        consulta_id: 1,
        duracion_ms: 10,
        modelo: 'modelo',
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const resultado = await consultar('¿cuanto?')

    expect(resultado.estado).toBe('Exitosa')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, opciones] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/consultar')
    expect(opciones.method).toBe('POST')
    expect(opciones.body).toContain('¿cuanto?')
  })

  it('traduce un 422 en error de validacion con el mensaje del servidor', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        respuestaJson({ detail: [{ loc: ['body', 'pregunta'], msg: 'es obligatorio' }] }, 422),
      ),
    )

    await expect(consultar('x')).rejects.toBeInstanceOf(ErrorValidacion)
  })

  it('traduce un 500 en error de servidor', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respuestaJson({ detail: 'error' }, 500)))

    await expect(consultar('x')).rejects.toBeInstanceOf(ErrorServidor)
  })

  it('reintenta contra la API directa si el origen no responde', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(respuestaJson([]))
    vi.stubGlobal('fetch', fetchMock)

    const historial = await obtenerHistorial()

    expect(historial).toEqual([])
    expect(fetchMock).toHaveBeenCalledTimes(2)
    const [primera, segunda] = fetchMock.mock.calls.map((llamada) => llamada[0] as string)
    expect(primera).toContain('/api/historial')
    expect(segunda).toContain('127.0.0.1:8000/api/historial')
  })

  it('reintenta si el origen devuelve HTML en vez de JSON', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response('<!doctype html><title>Walle</title>', {
          status: 200,
          headers: { 'Content-Type': 'text/html' },
        }),
      )
      .mockResolvedValueOnce(respuestaJson([]))
    vi.stubGlobal('fetch', fetchMock)

    const historial = await obtenerHistorial()

    expect(historial).toEqual([])
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('borra una consulta por indice', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(respuestaJson({ eliminado: true, indice: 3 }))
    vi.stubGlobal('fetch', fetchMock)

    await borrarConsulta(3)

    const [url, opciones] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/historial/3')
    expect(opciones.method).toBe('DELETE')
  })
})
