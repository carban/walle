import type { ConsultaHistorial, ConsultaResponse } from '../tipos'
import { ErrorServidor, ErrorValidacion } from '../tipos'

/**
 * URL base de la API.
 *
 * - Con VITE_API_URL vacia (por defecto) se usan rutas relativas: el navegador llama
 *   a su propio origen y el proxy de Vite reenvia a la API. Es el modo sin CORS.
 * - Con valor absoluto el navegador llama directo a la API (el origen del frontend
 *   debe estar en la allowlist WALLE_CORS_ORIGINS).
 */
const base = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

/**
 * URL de respaldo: se usa solo si la peticion relativa no llega a la API (por
 * ejemplo, si el build se sirve como estatico o con `npm run preview` sin proxy).
 */
const urlRespaldo = (import.meta.env.VITE_API_URL_FALLBACK ?? 'http://127.0.0.1:8000').replace(
  /\/+$/,
  '',
)

async function enviar(camino: string, opciones: RequestInit | undefined, prefijo: string) {
  try {
    return await fetch(`${prefijo}${camino}`, {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      ...opciones,
    })
  } catch (error) {
    if (prefijo) throw error
    // Sin servidor en este origen: se reintenta contra la API directa.
    return fetch(`${urlRespaldo}${camino}`, {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      ...opciones,
    })
  }
}

async function pedir<T>(camino: string, opciones?: RequestInit): Promise<T> {
  const respuesta = await enviar(camino, opciones, base)

  const contenido = respuesta.headers.get('content-type') ?? ''
  const esJson = contenido.includes('application/json')

  if (!esJson && !base) {
    // El origen actual devolvio otra cosa (por ejemplo, el index.html del build):
    // significa que no estamos hablando con la API, asi que se usa el respaldo.
    const reintento = await enviar(camino, opciones, urlRespaldo)
    return procesar<T>(reintento)
  }

  return procesar<T>(respuesta)
}

async function procesar<T>(respuesta: Response): Promise<T> {
  if (respuesta.status === 422) {
    throw new ErrorValidacion(await mensajeDeDetalle(respuesta))
  }

  if (!respuesta.ok) {
    throw new ErrorServidor('El servidor no pudo completar la consulta. Inténtalo de nuevo.')
  }

  try {
    return (await respuesta.json()) as T
  } catch {
    throw new ErrorServidor('La respuesta del servidor no se pudo interpretar.')
  }
}

async function mensajeDeDetalle(respuesta: Response): Promise<string> {
  try {
    const cuerpo = (await respuesta.json()) as { detail?: unknown }
    const detalle = cuerpo.detail
    if (typeof detalle === 'string') return detalle
    if (Array.isArray(detalle) && detalle.length > 0) {
      const primero = detalle[0] as { loc?: unknown[]; msg?: string }
      const campo = Array.isArray(primero.loc) ? primero.loc.at(-1) : undefined
      return campo
        ? `El campo "${String(campo)}" ${primero.msg ?? 'no es válido'}.`
        : (primero.msg ?? 'La consulta no es válida.')
    }
  } catch {
    // la respuesta no traia JSON: se usa el mensaje generico
  }
  return 'La consulta no es válida.'
}

export async function consultar(pregunta: string): Promise<ConsultaResponse> {
  return pedir<ConsultaResponse>('/api/consultar', {
    method: 'POST',
    body: JSON.stringify({ pregunta }),
  })
}

export async function obtenerHistorial(): Promise<ConsultaHistorial[]> {
  return pedir<ConsultaHistorial[]>('/api/historial')
}

export async function obtenerConsulta(indice: number): Promise<ConsultaHistorial> {
  return pedir<ConsultaHistorial>(`/api/historial/${indice}`)
}

export async function borrarConsulta(indice: number): Promise<void> {
  await pedir<{ eliminado: boolean; indice: number }>(`/api/historial/${indice}`, {
    method: 'DELETE',
  })
}
