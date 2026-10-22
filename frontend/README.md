# Frontend — Walle

Interfaz de consultas del asistente Walle: chat con panel lateral de historial, fuentes, estados de
respuesta y manejo de errores.

La documentación completa (arquitectura, configuración, ejecución y pruebas) está en el
[README del repositorio](../README.md).

## Comandos

```bash
npm install        # dependencias
npm run dev        # servidor de desarrollo en http://localhost:5173 (proxy /api -> :8000)
npm run test       # suite de Vitest + Testing Library
npm run typecheck  # TypeScript en modo estricto
npm run lint       # oxlint
npm run build      # genera dist/ (lo sirve la API solo si WALLE_SERVIR_FRONTEND=true)
```

## Conexión con la API

El cliente usa rutas relativas (`/api/...`) y el **proxy de Vite** las reenvía a
`http://127.0.0.1:8000`: el navegador nunca sale de su propio origen y no hay errores de CORS.
Para chamar a otra URL se define `VITE_API_URL` en `frontend/.env` (ver `frontend/.env.example`);
en ese caso el origen del frontend debe estar en la allowlist `WALLE_CORS_ORIGINS` de la API.

## Estructura

```
src/
├── App.tsx                 estado global y orquestación de cliente y panel
├── tipos.ts                tipos alineados con el contrato de la API
├── api/cliente.ts          cliente HTTP tipado (único punto de acceso a la API)
├── componentes/            Chat, Intercambio, Fuentes, PanelHistorial, Aviso
├── estilos/global.css      estilos en CSS puro, sin framework
└── __tests__/App.test.tsx  pruebas de componente
```
