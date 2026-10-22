import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

/**
 * Proxy de desarrollo: reenvia `/api` a la API del puerto 8000.
 *
 * Es la red de seguridad del modo "URL absoluta": si el navegador llama directo a
 * `http://127.0.0.1:8000` y esa llamada falla, el cliente reintenta por rutas
 * relativas y el proxy llega a la misma API.
 */
const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Si el puerto esta ocupado, Vite falla en vez de cambiar de puerto en
    // silencio: cambiarlo dejaba al navegador viendo otra aplicacion.
    strictPort: true,
    proxy,
  },
  preview: {
    port: 4173,
    strictPort: true,
    // El build servido con `npm run preview` necesita el proxy tambien: si no,
    // /api devuelve el index.html y el frontend se ve roto.
    proxy,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts', 'src/**/*.tsx'],
      exclude: ['src/main.tsx', 'src/__tests__/**'],
    },
  },
})
