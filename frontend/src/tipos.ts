/**
 * Tipos compartidos, alineados con el contrato de la API (`src/walle/api/esquema.py`).
 *
 * Se mantienen los nombres del JSON de la API (`consulta_id`, `duracion_ms`) para
 * que el mapeo con la respuesta sea directo y no fragile.
 */

/** Estados validos de una respuesta. */
export type Estado = 'Exitosa' | 'Sin información suficiente' | 'Bloqueada por seguridad'

/** Documento y fragmento que sustentan una respuesta. */
export interface Fuente {
  documento: string
  fragmento: string
}

/** Cuerpo de la peticion de consulta. */
export interface ConsultaRequest {
  pregunta: string
}

/** Respuesta de `POST /api/consultar`. */
export interface ConsultaResponse {
  respuesta: string
  fuentes: Fuente[]
  estado: Estado
  consulta_id: number | null
  duracion_ms: number
  modelo: string
}

/** Consulta registrada, tal y como la expone el historial. */
export interface ResumenConsulta {
  id: number
  pregunta: string
  fecha_hora: string
  respuesta: string
  fuentes: Fuente[]
  estado: Estado
  duracion_ms: number
  modelo: string
}

/** Resultado de eliminar una consulta del historial. */
export interface BorradoRespuesta {
  eliminado: boolean
  indice: number
}

/**
 * Par pregunta/respuesta ya resuelto, tal y como se muestra en el chat.
 *
 * `enCurso` distingue una consulta en vuelo (sin respuesta todavia) de una que
 * fallo: en el caso de error el intercambio se retira y el error se muestra aparte.
 */
export interface Intercambio {
  /** Clave de React. */
  id: string
  /** Indice que asigna el backend; `null` mientras la consulta no ha resuelto. */
  consultaId: number | null
  pregunta: string
  respuesta: ConsultaResponse | null
  enCurso: boolean
}

/** Error de validacion devuelto por la API (HTTP 422). */
export class ErrorValidacion extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ErrorValidacion'
  }
}

/** Error de red o de servidor: la consulta no pudo completarse. */
export class ErrorServidor extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ErrorServidor'
  }
}
