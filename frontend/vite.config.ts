import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

// El proxy hace que, en desarrollo, el navegador llame siempre a su propio origen
// (http://localhost:5173/api) y Vite reenvie la peticion a la API: sin CORS.
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
  },
})
