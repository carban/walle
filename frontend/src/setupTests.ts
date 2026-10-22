import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'

/**
 * `matchMedia` no existe en jsdom, pero la interfaz lo usa para detectar
 * pantallas estrechas (RNF-02). Se define un doble que devuelve `matches`
 * segun la anchura simulada.
 */
function instalarMatchMedia() {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (consulta: string) => ({
      matches: window.innerWidth <= 900,
      media: consulta,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}

instalarMatchMedia()

afterEach(() => {
  vi.restoreAllMocks()
})
