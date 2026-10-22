# Frontend de Walle

Interfaz web del asistente: chat de consultas y panel lateral con el historial.

## Instalación

Requiere Node.js ≥ 20. La API (backend) corre aparte, en el puerto 8000.

```bash
cd frontend
npm ci          # instala exactamente lo que dice package-lock.json
```

## Scripts

| Script | Qué hace |
|--------|----------|
| `npm run dev` | Servidor de desarrollo en <http://localhost:5173> |
| `npm run build` | Compila a `dist/` (con comprobación de tipos) |
| `npm run preview` | Sirve `dist/` en <http://localhost:4173> |
| `npm run test` | Suite de Vitest (sin red: todo esta mockeado) |
| `npm run coverage` | Suite con cobertura |
| `npm run typecheck` | `tsc --noEmit` en modo estricto |
| `npm run lint` | `oxlint` |

## Configuración

Las variables viven en `frontend/.env` (ver `.env.example`). Son `VITE_*`, asi que
las lee Vite en tiempo de build.

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | URL de la API a la que llama el navegador. **Vacía** ⇒ rutas relativas: la peticion sale al propio origen y el proxy de Vite la reenvia a la API |
| `VITE_API_URL_FALLBACK` | `http://127.0.0.1:8000` | URL de reintento si la principal no responde (build servido sin proxy) |

El navegador llama directo a la API del puerto 8000, asi que el origen del
frontend debe estar en `WALLE_CORS_ORIGINS` de la API, que por defecto acepta
`http://localhost:5173` y `http://127.0.0.1:5173`.

## Recursos de la API que usa

| Operacion | Peticion |
|-----------|----------|
| Consultar | `POST /api/consultar` |
| Listar historial | `GET /api/consultas?limite=200&desplazamiento=0` |
| Detalle | `GET /api/consultas/{id}` |
| Borrar | `DELETE /api/consultas/{id}` |
| Sonda | `GET /health` |

## Modo de un solo servicio

La API puede servir la compilacion del frontend (opt-in):

```bash
npm run build
cd .. && WALLE_SERVIR_FRONTEND=true uv run uvicorn walle.main:app --port 8000
```
