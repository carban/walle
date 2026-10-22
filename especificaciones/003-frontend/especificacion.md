# Especificación 003 — Frontend del asistente Walle

**Característica:** Interfaz web de consultas al asistente, con panel lateral de historial
**Versión:** 1.0 · Estado: para revisión
**Documentos relacionados:** `constitucion/constitucion.md`, `especificaciones/001-api/especificacion.md`, `especificaciones/002-persistencia/especificacion.md`, `especificaciones/003-frontend/plan.md`, `especificaciones/003-frontend/tareas.md`

---

## 1. Contexto

La API ya expone el ciclo completo de consulta (`POST /api/consultar`) y el historial persistido (`GET /api/historial`, `GET /api/historial/{id}`, `DELETE /api/historial/{id}`), pero el asesor necesita una interfaz donde escribir la pregunta, leer la respuesta con sus fuentes y recuperar consultas anteriores sin herramientas de línea de comandos.

El enunciado de la prueba exige que la interfaz permita **realizar consultas, visualizar la respuesta, visualizar las fuentes, visualizar errores y mostrar el estado de procesamiento**, y que se ejecute completamente de forma local. No se evalúa el diseño visual, pero sí que la solución sea operable de punta a punta.

La referencia de interacción es un chat: una columna principal con los intercambios y un panel lateral izquierdo con las consultas anteriores. El backend no mantiene memoria conversacional: cada consulta es independiente y se resuelve contra el corpus documental. La interfaz refleja esa realidad mostrando los intercambios como una secuencia, no como una conversación con contexto acumulado.

## 2. Objetivo

Proveer una interfaz web local que permita al asesor realizar consultas, leer la respuesta con sus fuentes y estado, y navegar por el historial de consultas anteriores desde un panel lateral, sin errores de consola y sin exponer información sensible.

## 3. Alcance

### 3.1 Dentro del alcance

- Aplicación React + TypeScript, compilada con Vite y gestionada con npm.
- Chat: campo de consulta, acción de enviar, indicador de estado de procesamiento, burbuja de respuesta y de pregunta.
- Visualización de fuentes (documento y fragmento) y del estado de la respuesta.
- Panel lateral con el historial: listado, selección de una consulta, borrado por índice y acción de nueva conversación.
- Manejo visible de errores: validación (422), red y servidor.
- Configuración de la URL de la API y de los orígenes permitidos (CORS) para que ambos servicios convivan en local.
- Estilos en CSS puro, sin librería de UI ni framework de estilos.

### 3.2 Fuera del alcance

- Autenticación, usuarios o roles.
- Memoria conversacional: el backend no recibe el historial como contexto de la pregunta.
- Envío de archivos, imágenes o audio.
- Streaming de la respuesta (decisión D-02): la respuesta llega completa.
- Persistencia en el navegador (`localStorage`, `sessionStorage`, cookies): la fuente de verdad es la base SQLite del backend.
- Tema oscuro, internacionalización y diseño visual avanzado (no se evalúa el diseño).
- Versión móvil nativa o empaquetado como PWA.

## 4. Requerimientos funcionales

### RF-01 — Realizar consultas
La interfaz ofrece un campo de texto multilínea y una acción de enviar. La consulta solo se envía si el campo contiene texto no vacío (tras eliminar espacios). Mientras la petición está en curso, la acción de envío se deshabilita y se muestra el estado de procesamiento, de modo que no se puedan lanzar consultas duplicadas por accidente. Al finalizar, el campo queda listo para una nueva consulta y el foco vuelve a él.

### RF-02 — Visualización de la respuesta
Cada consulta enviada y cada consulta recuperada del historial se muestran como un par de burbujas: la pregunta del usuario y la respuesta del asistente. La respuesta muestra su estado (`Exitosa`, `Sin información suficiente` o `Bloqueada por seguridad`) con una etiqueta visual distinguible, la duración de la consulta y el modelo utilizado cuando lo hubo. El texto se presenta tal cual lo devuelve la API, sin alterar su contenido ni sus saltos de línea.

### RF-03 — Visualización de las fuentes
Cuando la respuesta tiene fuentes, se muestran junto a ella como una lista de referencias, cada una con el nombre del documento y el fragmento que la sustenta. Cuando la respuesta no tiene fuentes, no se muestra el bloque de fuentes. Las fuentes nunca se inventan en el cliente: se muestran exactamente las que devuelve la API.

### RF-04 — Panel lateral con el historial
El panel lateral carga el historial al montar la aplicación y muestra las consultas de la más reciente a la más antigua, con la pregunta, la fecha y hora y el estado. Al seleccionar una consulta, se carga su detalle completo (respuesta y fuentes) en el chat. Cada entrada del panel permite borrar esa consulta, tras lo cual desaparece del listado y deja de estar disponible. La acción de nueva conversación limpia el chat visible sin eliminar el historial persistido.

### RF-05 — Visualización de errores y de estados
La interfaz distingue tres situaciones de fallo y las comunica de forma visible: (a) **validación**: la pregunta es inválida y se muestra el mensaje del servidor; (b) **conexión o servidor**: no se pudo completar la petición y se muestra un mensaje accionable; (c) **respuesta sin información suficiente** o **bloqueada por seguridad**: no es un error, se presenta como un estado normal de la respuesta, con su etiqueta correspondiente. En ningún caso se muestra una traza técnica ni un detalle interno del servidor. Un error nunca borra lo que el usuario ya tenía en pantalla.

## 5. Requerimientos no funcionales

### RNF-01 — Accesibilidad y usabilidad básica
Los controles tienen etiqueta asociada, se opera con teclado, mantienen el foco visible y el mensaje de error se anuncia a lectores de pantalla mediante una región `aria-live`. Los estados de las respuestas se distinguen también por texto, no solo por color. El chat es navegable con el teclado sin necesidad de puntero.

### RNF-02 — Comportamiento responsive
En pantallas anchas el panel lateral y el chat conviven; en pantallas estrechas el panel se puede ocultar y volver a mostrar sin perder el estado de la conversación ni el contenido del campo de consulta.

### RNF-03 — Rendimiento
La interfaz responde de forma inmediata a la interacción del usuario (escritura, envío, cambio de panel) sin esperas perceptibles; la latencia visible proviene del modelo y no de la renderización. El cliente HTTP no duplica peticiones y no bloquea la interfaz mientras espera.

### RNF-04 — Convivencia local sin fricción de CORS
La API acepta explícitamente los orígenes del servidor de desarrollo (por defecto `http://localhost:5173` y `http://127.0.0.1:5173`) y ninguna otra fuente sin autorización. La aplicación no registra errores de CORS en la consola ni en la red del navegador. Además, la compilación de producción se sirve desde la propia API, de modo que también existe un modo de un solo servicio donde el problema de origen no se produce.

### RNF-05 — Mantenibilidad
TypeScript en modo estricto, sin tipos implícitos `any`, componentes con una responsabilidad clara y un cliente HTTP único y tipado que centraliza la URL de la API y el manejo de errores. Sin dependencias de interfaz de terceros: el `package.json` solo contiene React, React DOM y las herramientas de build. Los scripts de npm están documentados y son reproducibles con `npm ci`.

## 6. Riesgos

| # | Riesgo | Impacto | Mitigación prevista |
|---|--------|---------|---------------------|
| R-01 | **Errores de CORS** por diferencia de origen (`localhost` frente a `127.0.0.1`) o por un puerto distinto al esperado | La interfaz no carga nada; el síntoma clásico es un error en la consola del navegador | Allowlist explícita de orígenes en la configuración de la API, preconfiguración del proxy de Vite hacia el backend y prueba de integración que valida la cabecera `Access-Control-Allow-Origin` |
| R-02 | **Desincronización entre el chat y el historial**: una consulta nueva no aparece en el panel o el panel no refleja un borrado | El asesor no confía en lo que ve o cree que hay datos duplicados | Tras cada consulta se refresca el historial; tras un borrado se actualiza el listado localmente y se reconcilia con el servidor; la respuesta siempre lleva su `consulta_id` para identificarla |
| R-03 | **Doble contabilización de consultas**: el cliente pinta la pregunta y el backend la registra, o el cliente la registra además | Historial con duplicados | Single source of truth: el backend es quien persiste y asigna el índice; el cliente solo refleja lo que devuelve la API |
| R-04 | **Inyección de contenido en el DOM** si se usara `dangerouslySetInnerHTML` con una respuesta del modelo | Ejecución de scripts en el navegador del asesor | Renderizado exclusivamente por React como texto plano; prohibición explícita de `dangerouslySetInnerHTML` y de `eval` en el código del cliente |
| R-05 | **Copia de datos sensibles en el navegador** por persistir la conversación en `localStorage` | La información clasificada quedaría en el disco del asesor, fuera del control de la base | El cliente no persiste nada en el navegador; el historial vive solo en el backend, que ya aplica los guardrails de salida antes de persistir |

## 7. Criterios de aceptación (Gherkin)

```gherkin
Característica: Interfaz web del asistente Walle

  Escenario: Consulta válida con respuesta y fuentes (RF-01, RF-02, RF-03)
    Dado que la API responde una consulta con estado "Exitosa" y una fuente del documento "Productos de Crédito.md"
    When el asesor escribe una pregunta y la envía
    Entonces se muestra la pregunta en una burbuja de usuario
    Y se muestra el estado de procesamiento mientras la petición está en curso
    Y al terminar se muestra la respuesta del asistente con la etiqueta "Exitosa"
    Y se muestra el bloque de fuentes con el nombre del documento y su fragmento
    Y el campo de consulta vuelve a estar vacío y listo para escribir

  Escenario: Pregunta vacía (RF-01)
    Dado que el campo de consulta está vacío
    When el asesor intenta enviar
    Entonces no se realiza ninguna petición al servidor
    Y el campo de consulta permanece vacío

  Escenario: No se pueden lanzar consultas duplicadas (RF-01)
    Dado que hay una consulta en curso
    When el asesor intenta enviar otra
    Entonces la acción de envío está deshabilitada
    Y solo una petición se encuentra en vuelo

  Escenario: Respuesta sin información suficiente (RF-02, RF-05)
    Dado que la API responde el estado "Sin información suficiente" con el mensaje canónico
    When la interfaz recibe la respuesta
    Entonces se muestra la etiqueta "Sin información suficiente"
    Y se muestra el texto exacto "No tengo información suficiente para responder."
    Y no se muestra ningún bloque de fuentes
    Y no se muestra un mensaje de error

  Escenario: Respuesta bloqueada por seguridad (RF-02, RF-05)
    Dado que la API responde el estado "Bloqueada por seguridad"
    When la interfaz recibe la respuesta
    Entonces se muestra la etiqueta "Bloqueada por seguridad"
    Y el mensaje mostrado es el genérico devuelto por la API
    Y no se muestran fuentes ni detalles técnicos

  Escenario: Error de validación del servidor (RF-05)
    Dado que la API responde 422 con el detalle del campo "pregunta"
    When la interfaz recibe la respuesta
    Entonces se muestra un aviso de error legible que menciona el campo "pregunta"
    Y no se muestra ninguna traza técnica
    Y el historial previo permanece visible

  Escenario: Error de red o de servidor (RF-05)
    Dado que la API no está disponible
    When el asesor envía una consulta
    Entonces se muestra un aviso de error que indica que no se pudo completar la consulta
    Y la interfaz sigue operativa para reintentar
    Y no se muestra el detalle técnico de la excepción

  Escenario: Panel lateral con el historial (RF-04)
    Dado que la API devuelve tres consultas del historial
    When la aplicación se carga
    Entonces el panel lateral muestra tres entradas
    Y cada entrada muestra la pregunta, la fecha y hora y el estado
    Y las entradas aparecen de la más reciente a la más antigua

  Escenario: Seleccionar una consulta del historial (RF-04)
    Dado que el historial contiene una consulta con respuesta y fuentes
    When el asesor hace clic en esa entrada
    Entonces el chat muestra la pregunta y la respuesta completas con sus fuentes
    Y el panel sigue mostrando el resto de las entradas

  Escenario: Borrar una consulta del historial (RF-04)
    Dado que el historial contiene tres consultas
    When el asesor borra una de ellas
    Entonces esa entrada desaparece del panel lateral
    Y el historial del servidor ya no la incluye
    Y las demás entradas permanecen

  Escenario: Nueva conversación (RF-04)
    Dado que hay consultas en el chat y en el historial
    When el asesor elige "Nueva conversación"
    Entonces el chat queda vacío
    Y el historial del panel lateral se mantiene intacto

  Escenario: Sin CORS en la ejecución local (RNF-04)
    Dado que la API se ejecuta en el puerto 8000 y el cliente en el puerto 5173
    When el navegador realiza una petición al backend
    Entonces la respuesta incluye la cabecera de origen permitido
    Y la consola del navegador no registra errores de CORS

  Escenario: Navegación por teclado y anuncio de errores (RNF-01)
    Dado que un asesor usa únicamente el teclado
    When enfoca el campo de consulta, escribe y envía con el teclado
    Entonces el foco permanece en un control identificable en todo momento
    Y el aviso de error se anuncia mediante una región "aria-live"

  Escenario: Pantalla estrecha (RNF-02)
    Dado que el dispositivo tiene un ancho reducido
    When el asesor oculta el panel lateral
    Entonces el chat sigue visible con su contenido actual
    Y el campo de consulta conserva lo escrito
```

## 8. Trazabilidad

| Requisito | Escenario Gherkin | Prueba prevista |
|-----------|------------------|-----------------|
| RF-01 | Consulta válida, pregunta vacía, sin duplicados | `frontend/src/__tests__/Chat.test.tsx` |
| RF-02 | Consulta válida, sin información suficiente, bloqueada | `frontend/src/__tests__/Chat.test.tsx` |
| RF-03 | Consulta válida | `frontend/src/__tests__/Chat.test.tsx` |
| RF-04 | Panel lateral, seleccionar, borrar, nueva conversación | `frontend/src/__tests__/PanelHistorial.test.tsx` |
| RF-05 | Error de validación, error de red, estados no erróneos | `frontend/src/__tests__/Chat.test.tsx` |
| RNF-01 | Teclado y `aria-live` | `frontend/src/__tests__/accesibilidad.test.tsx` |
| RNF-02 | Pantalla estrecha | `frontend/src/__tests__/PanelHistorial.test.tsx` |
| RNF-03 | Sin bloqueos de interfaz | `frontend/src/__tests__/Chat.test.tsx` |
| RNF-04 | Sin CORS en local | `tests/integration/test_cors.py` + prueba manual en navegador |
| RNF-05 | TypeScript estricto y cliente HTTP único | `npm run lint` + `npm run typecheck` |
