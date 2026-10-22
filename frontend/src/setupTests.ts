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
      matches: !consulta.includes('prefers-reduced-motion') && window.innerWidth <= 900,
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

// jsdom no implementa scrollIntoView: sin este doble el desplazamiento no existe.
Element.prototype.scrollIntoView = () => {}

instalarMatchMedia()
afterEach(() => {
  vi.restoreAllMocks()
})
