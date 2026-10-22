export type Estado = 'Exitosa' | 'Sin información suficiente' | 'Bloqueada por seguridad'

export interface Fuente {
  documento: string
  fragmento: string
}

export interface ConsultaResponse {
  respuesta: string
  fuentes: Fuente[]
  estado: Estado
  consulta_id: number | null
  duracion_ms: number
  modelo: string
}

export interface ConsultaHistorial {
  id: number
  pregunta: string
  fecha_hora: string
  respuesta: string
  fuentes: Fuente[]
  estado: Estado
  duracion_ms: number
  modelo: string
}

export interface Intercambio {
  id: string
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
