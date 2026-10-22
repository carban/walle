# Plan 003 — Frontend del asistente Walle

**Característica:** Interfaz web de consultas al asistente, con panel lateral de historial
**Versión:** 1.0 · Estado: para revisión
**Especificación:** `especificaciones/003-frontend/especificacion.md`
**Tareas:** `especificaciones/003-frontend/tareas.md`

---

## 1. Arquitectura propuesta

```
┌───────────────────────── Navegador ─────────────────────────────────┐
│  ┌───────────────────┐   ┌──────────────────────────────────────┐  │
│  │  PanelHistorial   │   │              Chat                     │  │
│  │  (aside, 280px)   │   │  ┌──────────────────────────────┐    │  │
│  │  · cabecera       │   │  │ Intercambios (lista)          │    │  │
│  │  · botón nueva    │   │  │  ├ Burbuja usuario            │    │  │
│  │    conversación   │   │  │  └ Burbuja asistente          │    │  │
│  │  · lista de       │   │  │      · etiqueta de estado     │    │  │
│  │    consultas      │   │  │      · texto de la respuesta  │    │  │
│  │    (pregunta,     │   │  │      · bloque de fuentes      │    │  │
│  │     fecha, estado,│   │  └──────────────────────────────┘    │  │
│  │     botón borrar) │   │  ┌──────────────────────────────┐    │  │
│  │                   │   │  │ Campo de consulta + Enviar   │    │  │
│  └───────────────────┘   └──┴──────────────┬───────────────────┘  │
└───────────────────────────────────────────┼──────────────────────────┘
                                            │ cliente HTTP tipado
                    ┌───────────────────────▼──────────────────────┐
                    │  API FastAPI  http://127.0.0.1:8000            │
                    │  POST /api/consultar                          │
                    │  GET  /api/historial   GET/DELETE /api/historial/{id}
                    │  CORS: http://localhost:5173, http://127.0.0.1:5173
                    └──────────────────────────────────────────────┘
```

### 1.1 Estructura de carpetas

```
frontend/
├── package.json
├── package-lock.json
├── tsconfig.json               # TypeScript estricto
├── tsconfig.node.json
├── vite.config.ts              # plugin de React + proxy /api → 127.0.0.1:8000
├── index.html
└── src/
    ├── main.tsx                # punto de entrada
    ├── App.tsx                 # composición: panel + chat
    ├── tipos.ts                # ConsultaRequest, ConsultaResponse, Fuente, Estado, ResumenConsulta
    ├── api/
    │   └── cliente.ts          # cliente HTTP tipado (único punto de acceso a la API)
    ├── componentes/
    │   ├── PanelHistorial.tsx
    │   ├── Chat.tsx
    │   ├── Intercambio.tsx     # par pregunta/respuesta
    │   ├── Fuentes.tsx
    │   └── Aviso.tsx           # banner de error (aria-live)
    ├── estilos/
    │   ├── global.css          # variables CSS, reset, layout
    │   └── componentes.css
    └── __tests__/              # pruebas con Vitest + Testing Library
```

### 1.2 Modelo de estado

Un único estado en `App.tsx` con `useState`/`useReducer`:

```ts
type EstadoApp = {
  intercambios: Intercambio[];       // orden cronológico de lo que se ve en el chat
  historial: ResumenConsulta[];      // lo que muestra el panel lateral
  enCurso: boolean;                  // hay una petición en vuelo
  aviso: Aviso | null;               // error visible (validación, red o servidor)
  panelVisible: boolean;             // responsive
};
```

`Intercambio` modela un par pregunta/respuesta ya resuelto:

```ts
type Intercambio = {
  id: string;                        // clave de React
  consultaId: number | null;         // índice que asigna el backend
  pregunta: string;
  respuesta: ConsultaResponse | null;
  enCurso: boolean;                  // true mientras se espera la respuesta
};
```

**Flujo de una consulta nueva**

```
1. El usuario escribe y envía
2. Se añade un intercambio con enCurso = true y enCurso global = true
3. POST /api/consultar
4a. Éxito → se completa el intercambio con la respuesta y su consultaId
4b. Error   → el intercambio se marca con respuesta = null y se muestra un aviso
5. En ambos casos: enCurso = false y se refresca el historial (GET /api/historial)
```

**Flujo de "Nueva conversación"**: se vacía `intercambios` y se limpia el aviso. El historial no se toca.

**Flujo de selección en el historial**: se pide el detalle (`GET /api/historial/{id}`) y se añade el intercambio correspondiente al chat, sin borrar lo que ya había.

**Flujo de borrado**: se llama a `DELETE /api/historial/{id}`; si responde 200, se quita la entrada del `historial` local y, si estaba visible en el chat, se marca o se retira. Después se refresca el historial para reconciliar.

### 1.3 Cliente HTTP tipado

Un único módulo `src/api/cliente.ts` con la URL base leída de `import.meta.env.VITE_API_URL` (por defecto `http://127.0.0.1:8000`) y estas funciones:

```ts
consultar(pregunta: string): Promise<ConsultaResponse>
obtenerHistorial(): Promise<ResumenConsulta[]>
obtenerConsulta(id: number): Promise<DetalleConsulta>
borrarConsulta(id: number): Promise<void>
```

Reglas:

- Todas las peticiones usan `Content-Type: application/json` y `Accept: application/json`.
- Un `422` se convierte en un error de tipo `ErrorValidacion` con el mensaje del servidor; un error de red o `5xx` en `ErrorServidor`; ambos llevan un mensaje apto para mostrar.
- Nunca se muestra la traza ni el `stack` al usuario.
- Con `VITE_API_URL` vacío, el cliente usa rutas relativas (`/api/...`), lo que permite el modo de un solo servicio (la API sirve `dist/`).

### 1.4 CORS y ejecución local

| Aspecto | Desarrollo | Producción local |
|---------|-----------|------------------|
| Origen del cliente | `http://localhost:5173` | `http://127.0.0.1:8000` (mismo origen) |
| URL de la API | `http://127.0.0.1:8000` | relativa (`/api`) |
| CORS | Allowlist en la API: `http://localhost:5173`, `http://127.0.0.1:5173` | No aplica (mismo origen) |
| Proxy de Vite | `/api` → `http://127.0.0.1:8000` (evita CORS incluso) | No aplica |

Decisiones para que no haya errores de CORS:

1. La API declara los orígenes de desarrollo en su configuración (`WALLE_CORS_ORIGINS`), con `localhost` **y** `127.0.0.1` (los navegadores los tratan como orígenes distintos).
2. El proxy de Vite hace que, en desarrollo, el navegador llame a `http://localhost:5173/api/...` y Vite reenvíe a la API: la petición nunca es de origen cruzado. El allowlist de CORS queda como red de seguridad (p. ej. si alguien abre el front en otro puerto).
3. Las credenciales de la API se aplican solo a orígenes de la allowlist, nunca con comodín.

### 1.5 Estilos (CSS puro)

- `global.css` define las variables del tema (`--color-fondo`, `--color-texto`, `--color-acento`, `--color-error`, `--color-borde`, `--color-usuario`, `--color-asistente`), el reset y el layout en dos columnas con `grid`.
- El panel lateral se oculta por debajo de 900 px de ancho y se puede abrir y cerrar con un botón (estado `panelVisible`).
- Los estados tienen color **y** texto: `Exitosa` (verde), `Sin información suficiente` (ámbar), `Bloqueada por seguridad` (rojo).
- Sin dependencias de estilos: ni Tailwind, ni Bootstrap, ni librerías de componentes.

### 1.6 Pruebas del frontend

- **Vitest + @testing-library/react + jsdom** como base de la suite.
- `msw` no es necesario: las pruebas mockean el módulo `src/api/cliente.ts` con `vi.mock`.
- Casos: envío de consulta, estado vacío, error 422, error de red, estados de la respuesta, renderizado de fuentes, listado del historial, selección, borrado y nueva conversación.
- `npm run typecheck` (`tsc --noEmit`) y `npm run lint` (ESLint con la configuración oficial de Vite) como puertas obligatorias.

## 2. Componentes

| Componente | Responsabilidad | Requisitos |
|------------|-----------------|------------|
| `App.tsx` | Estado global de la UI, orquestación de cliente y panel | RF-01, RF-04, RF-05 |
| `Chat.tsx` | Lista de intercambios, campo de consulta, acción de enviar, estado de carga | RF-01, RF-02 |
| `Intercambio.tsx` | Par pregunta/respuesta con etiqueta de estado, duración y modelo | RF-02 |
| `Fuentes.tsx` | Bloque de referencias (documento + fragmento) | RF-03 |
| `PanelHistorial.tsx` | Listado del historial, selección, borrado, nueva conversación | RF-04 |
| `Aviso.tsx` | Banner de error con `role="alert"` y región `aria-live` | RF-05, RNF-01 |
| `api/cliente.ts` | Cliente HTTP tipado y traducción de errores | RNF-04, RNF-05 |
| `tipos.ts` | Tipos compartidos alineados con el contrato de la API | RNF-05 |

## 3. Estrategia de pruebas

| Suite | Contenido | Herramientas |
|-------|-----------|--------------|
| `frontend/src/__tests__/` | Chat, PanelHistorial, accesibilidad | Vitest, Testing Library, jsdom |
| `npm run typecheck` | TypeScript estricto sin errores | `tsc --noEmit` |
| `npm run lint` | ESLint (configuración oficial de Vite) | ESLint |
| `tests/integration/test_cors.py` (backend) | Cabecera `Access-Control-Allow-Origin` para los orígenes permitidos y ausencia para los no permitidos | pytest + TestClient |
| Manual | Recorrido completo en el navegador: consulta, fuentes, panel, borrado, error de red | Checklist en el README |

**Criterio de aceptación de la suite**: `npm run test` en verde sin red (todas las peticiones están mockeadas) y `npm run build` genera `dist/` sin avisos de TypeScript.

## 4. Riesgos de implementación y mitigación

| Riesgo | Mitigación en el plan |
|--------|----------------------|
| CORS por `localhost` vs `127.0.0.1` | Allowlist con ambos, proxy de Vite y prueba de integración del backend |
| Divergencia entre tipos del cliente y contrato real de la API | `tipos.ts` derivado del esquema de la API; una prueba de contrato en el backend valida el JSON de ejemplo |
| Desincronización del panel | Refresco del historial tras cada mutación y `consulta_id` como clave de reconciliación |
| Regresiones de accesibilidad | Pruebas con Testing Library sobre roles y `aria-live` |
| Crecimiento del `package.json` | Solo React, React DOM y herramientas de build; revisión del `package.json` al cierre de la característica |
