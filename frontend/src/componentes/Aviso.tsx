interface Props {
  mensaje: string
  onReintentar?: () => void
}

/** Banner de error visible y anunciado a lectores de pantalla. */
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
