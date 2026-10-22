/**
 * Cliente HTTP tipado: unico punto de acceso a la API.
 *
 * Toda la app consume el backend a traves de este modulo, de modo que la URL de
 * la API y la traduccion de errores estan centralizadas (RNF-05).
 */

import type {
  BorradoRespuesta,
  ConsultaResponse,
  ResumenConsulta,
} from '../tipos'
import { ErrorServidor, ErrorValidacion } from '../tipos'

/**
 * URL base de la API.
 *
 * Por defecto es la API local del puerto 8000 (`http://127.0.0.1:8000`): el
 * navegador llama directamente a la API y el origen del frontend esta en la
 * allowlist `WALLE_CORS_ORIGINS` de la API, que lo permite por defecto.
 *
 * Con `VITE_API_URL` vacia se usan rutas relativas: la peticion sale hacia el
 * propio origen y el proxy de Vite la reenvia a la API. Ese modo sirve de red de
 * seguridad cuando el frontend se sirve sin proxy.
 */
const base = normalizar(import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000')

/**
 * URL de respaldo: se usa solo si la peticion principal no llega a la API
 * (por ejemplo, si el build se sirve como estatico, sin proxy de Vite).
 */
const respaldo = normalizar(
  import.meta.env.VITE_API_URL_FALLBACK ?? 'http://127.0.0.1:8000',
)

/** Ruta del recurso de consultas en la API. */
const RECURSO = '/api/consultas'

/** Pagina maxima que se pide al listar el historial. */
const LIMITE_PAGINA = 200

function normalizar(url: string): string {
  return url.replace(/\/+$/, '')
}

/**
 * Ejecuta una peticion HTTP hacia la API.
 *
 * Si la URL principal no responde (la API no esta levantada o no es alcanzable
 * desde el navegador), reintenta contra la URL de respaldo. Devuelve la respuesta
 * sin interpretar para que cada llamador decida que hacer con el codigo.
 */
async function enviar(camino: string, opciones: RequestInit | undefined, prefijo: string) {
  const cabeceras = { 'Content-Type': 'application/json', Accept: 'application/json' }
  try {
    return await fetch(`${prefijo}${camino}`, { headers: cabeceras, ...opciones })
  } catch {
    if (prefijo === respaldo) {
      throw new ErrorServidor(mensajeDeConexion())
    }
    // El prefijo principal no respondio: se reintenta contra el respaldo.
    try {
      return await fetch(`${respaldo}${camino}`, { headers: cabeceras, ...opciones })
    } catch {
      throw new ErrorServidor(mensajeDeConexion())
    }
  }
}

/** Mensaje accionable para un fallo de conexion: dice como levantar la API. */
function mensajeDeConexion(): string {
  return (
    `No se pudo contactar la API en ${respaldo}. ` +
    'Comprueba que este levantada con: uv run uvicorn walle.main:app --port 8000'
  )
}

/** Ejecuta la peticion y devuelve el cuerpo JSON ya interpretado. */
async function pedir<T>(camino: string, opciones?: RequestInit): Promise<T> {
  const respuesta = await enviar(camino, opciones, base)
  return procesar<T>(respuesta)
}

/** Traduce el codigo de estado y el cuerpo de la respuesta en un resultado o un error. */
async function procesar<T>(respuesta: Response): Promise<T> {
  if (respuesta.status === 422) {
    throw new ErrorValidacion(await mensajeDeValidacion(respuesta))
  }

  if (respuesta.status === 404) {
    throw new ErrorServidor('La consulta solicitada no existe en el historial.')
  }

  if (!respuesta.ok) {
    // El proxy de Vite responde 502/503/504 cuando no consigue hablar con la API.
    if ([502, 503, 504].includes(respuesta.status)) {
      throw new ErrorServidor(mensajeDeConexion())
    }
    throw new ErrorServidor('El servidor no pudo completar la consulta. Inténtalo de nuevo.')
  }

  try {
    return (await respuesta.json()) as T
  } catch {
    throw new ErrorServidor('La respuesta del servidor no se pudo interpretar.')
  }
}

/**
 * Extrae el mensaje de validacion del servidor.
 *
 * FastAPI devuelve `detail` como cadena o como lista de errores por campo. Se
 * construye un mensaje legible que identifica el campo, sin reproducir trazas.
 */
async function mensajeDeValidacion(respuesta: Response): Promise<string> {
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
    // La respuesta no traia JSON: se usa el mensaje generico.
  }
  return 'La consulta no es válida.'
}

/** Realiza una consulta al asistente. */
export async function consultar(pregunta: string): Promise<ConsultaResponse> {
  return pedir<ConsultaResponse>('/api/consultar', {
    method: 'POST',
    body: JSON.stringify({ pregunta }),
  })
}

/** Lista el historial de consultas, de la mas reciente a la mas antigua. */
export async function obtenerHistorial(): Promise<ResumenConsulta[]> {
  return pedir<ResumenConsulta[]>(`${RECURSO}?limite=${LIMITE_PAGINA}&desplazamiento=0`)
}

/** Obtiene el detalle de una consulta del historial. */
export async function obtenerConsulta(indice: number): Promise<ResumenConsulta> {
  return pedir<ResumenConsulta>(`${RECURSO}/${indice}`)
}

/** Elimina una consulta del historial. */
export async function borrarConsulta(indice: number): Promise<BorradoRespuesta> {
  return pedir<BorradoRespuesta>(`${RECURSO}/${indice}`, {
    method: 'DELETE',
  })
}
