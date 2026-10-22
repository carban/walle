import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// El proxy hace que, en desarrollo, el navegador llame siempre a su propio origen
// (http://localhost:5173/api) y Vite reenvie la peticion a la API: sin CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
    css: false,
  },
})
