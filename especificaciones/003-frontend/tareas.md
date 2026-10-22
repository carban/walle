# Tareas 003 — Frontend del asistente Walle

**Característica:** Interfaz web de consultas al asistente, con panel lateral de historial
**Versión:** 1.0 · Estado: para revisión
**Especificación:** `especificaciones/003-frontend/especificacion.md` · **Plan:** `especificaciones/003-frontend/plan.md`

**Convenciones**
- Tareas numeradas desde `T-201` para no solaparse con las características 001 y 002.
- TDD en el frontend: primero la prueba con Testing Library, después el componente.
- Solo dependencias de React, React DOM y herramientas de build; nada de librerías de UI.

---

## Fase 1 — Cimientos del frontend

- [ ] **T-201** Crear el proyecto con Vite + React + TypeScript en `frontend/` (`npm create vite@latest frontend -- --template react-ts`), con `npm install` y `package-lock.json` versionado.
  - Criterio: `npm run dev` levanta la aplicación y `npm run build` genera `dist/`.
- [ ] **T-202** Configurar TypeScript estricto (`"strict": true`, `noUncheckedIndexedAccess`, `noUnusedLocals`), ESLint con la configuración oficial de Vite y los scripts `dev`, `build`, `preview`, `test`, `typecheck`, `lint`.
  - Criterio: `npm run typecheck` y `npm run lint` en verde sobre la app inicial.
- [ ] **T-203** Configurar Vitest + Testing Library + jsdom, con `setupTests.ts` y el plugin de cobertura; añadir `test` al script de build de CI local.
  - Criterio: `npm run test` ejecuta una prueba de humo en verde.
- [ ] **T-204** Configurar `vite.config.ts` con el plugin de React y el proxy `/api` → `http://127.0.0.1:8000` con `changeOrigin: true`.
  - Criterio: desde el navegador, `fetch('/api/salud')` en `:5173` llega a la API sin error de CORS.
- [ ] **T-205** Definir `src/tipos.ts` alineado con el contrato de la API: `Estado`, `Fuente`, `ConsultaResponse`, `ResumenConsulta`, `DetalleConsulta`, `ErrorValidacion`, `ErrorServidor`.
  - Criterio: los tipos coinciden con el esquema de `src/walle/api/esquema.py` (revisión cruzada en el checklist final).

## Fase 2 — Cliente HTTP

- [ ] **T-206** Implementar `src/api/cliente.ts`: URL base desde `import.meta.env.VITE_API_URL` (por defecto `http://127.0.0.1:8000`, vacío ⇒ rutas relativas), `consultar`, `obtenerHistorial`, `obtenerConsulta`, `borrarConsulta`.
  - Criterio: pruebas unitarias con `fetch` simulado verifican URL, método y cuerpo de cada llamada.
- [ ] **T-207** Traducir errores: `422` → `ErrorValidacion` con el mensaje del servidor; fallo de red o `5xx` → `ErrorServidor` con mensaje accionable; nunca incluir `stack` ni trazas.
  - Criterio: `tests/cliente.test.ts` cubre 200, 422, 500 y excepción de red.

## Fase 3 — Estilos y layout

- [ ] **T-208** Escribir `src/estilos/global.css`: variables de tema, reset, layout en dos columnas con `grid`, tipografía base y estilos de foco visible.
  - Criterio: el layout es estable a 1440 px y a 480 px de ancho.
- [ ] **T-209** Implementar el comportamiento responsive: por debajo de 900 px el panel se oculta y un botón lo muestra/oculta sin perder el estado.
  - Criterio: prueba de `App` que comprueba la visibilidad del panel en ancho reducido.

## Fase 4 — Chat

- [ ] **T-210** Implementar `src/componentes/Aviso.tsx`: banner con `role="alert"` y región `aria-live="polite"`, con mensaje y acción opcional de reintento.
  - Criterio: `accesibilidad.test.tsx` encuentra el aviso por rol.
- [ ] **T-211** Implementar `src/componentes/Fuentes.tsx`: lista de fuentes con documento y fragmento; no renderiza nada si la lista está vacía.
  - Criterio: prueba que verifica el texto de la fuente y la ausencia del bloque con lista vacía.
- [ ] **T-212** Implementar `src/componentes/Intercambio.tsx`: burbuja de usuario, burbuja de asistente, etiqueta de estado con color y texto, duración y modelo.
  - Criterio: prueba que verifica los tres estados y que el texto de la respuesta se muestra tal cual, con sus saltos de línea.
- [ ] **T-213** Implementar `src/componentes/Chat.tsx`: lista de intercambios, campo multilínea, acción de enviar, deshabilitado mientras hay una petición en curso, foco de vuelta al campo al terminar, `Enter` envía y `Shift+Enter` salta de línea.
  - Criterio: prueba que verifica el envío, la desactivación durante la carga y que la pregunta vacía no dispara la petición.
- [ ] **T-214** Implementar el envío en `App.tsx`: alta del intercambio en curso, resolución con la respuesta, `consulta_id` almacenado y refresco del historial al terminar.
  - Criterio: prueba que verifica la secuencia pregunta → carga → respuesta → refresco del historial.

## Fase 5 — Panel lateral

- [ ] **T-215** Implementar `src/componentes/PanelHistorial.tsx`: carga del historial al montar, entradas con pregunta, fecha y hora y estado, más la acción de nueva conversación.
  - Criterio: prueba con tres entradas que verifica el orden y el contenido.
- [ ] **T-216** Implementar la selección de una consulta: `GET /api/historial/{id}` y muestra del intercambio completo en el chat sin borrar lo anterior.
  - Criterio: prueba que verifica que el detalle se pide y se pinta.
- [ ] **T-217** Implementar el borrado por índice: `DELETE /api/historial/{id}`, actualización optimista del listado y reconciliación posterior con el servidor.
  - Criterio: prueba que verifica la llamada, la desaparición de la entrada y el refresco final.
- [ ] **T-218** Implementar "Nueva conversación": vacía el chat, conserva el historial y limpia el aviso.
  - Criterio: prueba que verifica que el historial no cambia.

## Fase 6 — Estados y errores

- [ ] **T-219** Manejar el error de validación (422): mostrar el mensaje del servidor mencionando el campo, sin trazas, sin borrar el historial visible.
  - Criterio: prueba con `ErrorValidacion` simulado.
- [ ] **T-220** Manejar el error de red o de servidor: aviso accionable, interfaz operativa para reintentar, sin detalle técnico.
  - Criterio: prueba con `ErrorServidor` simulado.
- [ ] **T-221** Tratar "Sin información suficiente" y "Bloqueada por seguridad" como respuestas normales, no como errores.
  - Criterio: prueba que verifica que no se renderiza el componente `Aviso` en esos casos.

## Fase 7 — Integración con el backend

- [ ] **T-222** Verificar la allowlist de CORS del backend: `http://localhost:5173` y `http://127.0.0.1:5173` aceptados, otros rechazados; escribir la prueba `tests/integration/test_cors.py`.
  - Criterio: la prueba pasa y no hay peticiones con comodín.
- [ ] **T-223** Servir `frontend/dist` desde FastAPI como SPA (fallback a `index.html` para rutas del cliente) y comprobar el modo de un solo servicio.
  - Criterio: `npm run build` seguido de `uvicorn` sirve la aplicación en `http://127.0.0.1:8000`.
- [ ] **T-224** Recorrido manual completo en el navegador: consulta con fuentes, respuesta insuficiente, intento bloqueado, panel lateral, borrado, nueva conversación, error de red con la API detenida.
  - Criterio: checklist completado y documentado en el README.

## Fase 8 — Documentación de la característica

- [ ] **T-225** Documentar en `README.md` la sección del frontend: instalación con npm, `npm run dev`, `npm run build`, `npm run test`, variables `VITE_API_URL` y `WALLE_CORS_ORIGINS`, y el modo de un solo servicio.
- [ ] **T-226** Registrar en `docs/Cuestionario.md` las respuestas de la interfaz y de la operación local.
- [ ] **T-227** Revisar la matriz de trazabilidad §8 de la especificación: cada RF/RNF con al menos una prueba.
- [ ] **T-228** Verificar que `package.json` no contiene dependencias de UI de terceros y que `package-lock.json` está versionado.

---

## Dependencias entre tareas

```
T-201 → T-202 → T-203 → T-204 → T-205 → T-206 → T-207
                                              ↓
                    T-208 → T-209 → T-210 → T-211 → T-212 → T-213 → T-214
                                                                      ↓
                    T-215 → T-216 → T-217 → T-218
                                              ↓
                    T-219 → T-220 → T-221 → T-222 → T-223 → T-224
                                              ↓
                    T-225 → T-226 → T-227 → T-228
```

## Criterio de cierre de la característica 003

- `npm run test`, `npm run typecheck` y `npm run lint` en verde sin red.
- `npm run build` genera `dist/` sin errores de tipos.
- La aplicación funciona con dos servicios (`npm run dev` + `uvicorn`) sin errores de CORS en la consola del navegador.
- La aplicación funciona también en modo de un solo servicio servida por la API.
- Los 5 RF y los 5 RNF cubiertos por pruebas (matriz §8 verificada).
- El recorrido manual del backend y del frontend queda documentado en el README.
