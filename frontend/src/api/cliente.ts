import type { ConsultaHistorial, ConsultaResponse } from '../tipos'
import { ErrorServidor, ErrorValidacion } from '../tipos'

/**
 * URL base de la API. Con VITE_API_URL vacia se usan rutas relativas, que es el
 * modo de un solo servicio (la API sirve la compilacion del frontend).
 */
const base = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '')

function ruta(camino: string): string {
  return `${base}${camino}`
}

async function pedir<T>(camino: string, opciones?: RequestInit): Promise<T> {
  let respuesta: Response
  try {
    respuesta = await fetch(ruta(camino), {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      ...opciones,
    })
  } catch {
    throw new ErrorServidor('No se pudo conectar con el servidor. Revisa que la API esté en ejecución.')
  }

  if (respuesta.status === 422) {
    throw new ErrorValidacion(await mensajeDeDetalle(respuesta))
  }

  if (!respuesta.ok) {
    throw new ErrorServidor('El servidor no pudo completar la consulta. Inténtalo de nuevo.')
  }

  return (await respuesta.json()) as T
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
