/**
 * Componentes de presentacion: aviso de error, fuentes e intercambio.
 */

interface Props {
  mensaje: string
  onReintentar?: () => void
}

/**
 * Banner de error visible y anunciado a lectores de pantalla (RF-05, RNF-01).
 *
 * `role="alert"` junto con `aria-live` hace que el mensaje se anuncie sin que
 * el asesor tenga que buscarlo en la pantalla.
 */
export function Aviso({ mensaje, onReintentar }: Props) {
  return (
    <div className="aviso" role="alert" aria-live="assertive">
      <span className="aviso__texto">{mensaje}</span>
      {onReintentar ? (
        <button type="button" className="boton boton--secundario" onClick={onReintentar}>
          Reintentar
        </button>
      ) : null}
    </div>
  )
}
