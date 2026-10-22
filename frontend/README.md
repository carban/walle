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
npm run build      # genera dist/, que la API sirve como SPA
```

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
