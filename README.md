# Walle — Asistente interno para asesores comerciales

Walle responde consultas sobre **productos de crédito, microseguros, inversiones, criptomoneda,
procedimientos operativos y políticas internas**, fundamentando **toda** respuesta en la
documentación de `Data/` y citando sus fuentes. Es un sistema interno: la prioridad es la confianza
y la protección de la información, no la sofisticación del modelo.

Una respuesta sin evidencia documental no se emite. Cuando la información no está en el corpus, el
asistente lo dice exactamente: *"No tengo información suficiente para responder."*

---

## 1. Descripción

El asistente se compone de tres piezas:

| Capa | Tecnología | Responsabilidad |
|------|-----------|-----------------|
| API | Python 3.12 + FastAPI + `uv` | Valida, decide, invoca al modelo, valida la salida y expone el historial |
| Persistencia | SQLite (biblioteca estándar) | Registra cada consulta: pregunta, fecha y hora, respuesta, fuentes y estado |
| Frontend | React 19 + TypeScript + Vite (npm) | Chat con panel lateral de historial, fuentes, estados y errores |

El flujo completo de una consulta:

```
pregunta
  → (1) validación de entrada ............ 422 si es inválida
  → (2) guardrail anti-inyección ......... "Bloqueada por seguridad" (sin llamar al modelo)
  → (3) recuperación documental (BM25) ... sin documento relevante ⇒ "Sin información suficiente"
  → (4) modelo (OpenRouter, gratis) ...... con el documento completo, sin trocear
  → (5) validación de la salida .......... si contiene material sensible, se descarta
  → (6) respuesta + fuentes ............... se registra en SQLite
```

## 2. Arquitectura

```
                    ┌──────────────────────────────────────────┐
   Navegador ──────▶│            FastAPI (capa api)           │
   React (Vite)    │  POST /api/consultar                      │
                    │  GET  /api/historial · /api/historial/{id}│
                    │  DELETE /api/historial/{id}               │
                    │  GET  /api/salud · /api/documentos        │
                    └───────────────┬──────────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────────┐
                    │   Orquestador (dominio/consulta.py)      │
                    └──┬────────────┬─────────────┬───────────┘
                       │            │             │
       ┌───────────────▼──┐  ┌──────▼────────┐  ┌▼──────────────────┐
       │ seguridad/       │  │ recuperacion/ │  │ modelo/           │
       │ · inyeccion.py   │  │ · corpus.py   │  │ · cliente.py      │
       │ · sensibles.py   │  │ · bm25.py     │  │ · prompt.py       │
       │ · trazas.py      │  │ · relevance.py│  └▼──────────────────┘
       └──────────────────┘  │ · fuentes.py  │     OpenRouter (gratis)
                             └───────────────┘          │ falla
                                                       ▼
                                             fallback/extractivo.py
                                                   (determinista, local)
                                    │
                    ┌───────────────▼──────────────────────────┐
                    │  persistencia/repositorio.py              │
                    │  Protocolo · SQLite · memoria (respaldo) │
                    └──────────────────────────────────────────┘
```

### Decisiones de diseño relevantes

- **Sin chunking**: los siete documentos permitidos son pequeños; se envía el documento **completo**
  al modelo. Trocearlos no aporta precisión y complica la trazabilidad de las fuentes.
- **Recuperación BM25**: Okapi BM25 sobre el documento completo y sobre cada sección, complementado
  con sinónimos del dominio, entidades y moneda. El umbral `WALLE_UMBRAL_RELEVANCIA` decide si se
  invoca al modelo.
- **Allowlist explícita de documentos**: solo se cargan los siete documentos permitidos.
  `Data/Información restringida.md` **nunca** se abre, indexa, cita ni persiste.
- **La IA redacta; el sistema decide**: los estados válidos, los documentos permitidos y el criterio
  de suficiencia están en código, no en el prompt.
- **Protocolo de persistencia**: la API no depende de SQLite, lo que permite el modo degradado a
  memoria y una futura migración de motor sin reescribir la aplicación.

### Cómo ampliar el corpus

Los dos documentos incorporados (`Inversiones.md` y `Criptomoneda.md`) quedaron registrados en:

1. `Data/`: el archivo Markdown con el contenido.
2. `src/walle/config.py`: la allowlist `DOCUMENTOS_PERMITIDOS`.
3. `src/walle/recuperacion/relevance.py`: `_GRUPOS_SINONIMOS` y `_ENTIDADES` cuando el documento
   introduce vocabulario o productos nuevos.
4. `tests/`: el conteo de `corpus.documentos` en `tests/integration/test_api_consulta.py` y las
   pruebas de recuperación del nuevo dominio.
5. Documentación: conteo en `README.md`, `001-api/especificacion.md` y `001-api/plan.md`.

El documento restringido no se toca: sigue fuera de la allowlist y nunca se abre.

### Los tres estados de respuesta

| Estado | Significado | Fuentes |
|--------|-------------|---------|
| `Exitosa` | Respuesta sustentada en la documentación | Sí, con documento y sección |
| `Sin información suficiente` | No hay evidencia documental suficiente | Vacías |
| `Bloqueada por seguridad` | Intento de obtener material restringido o de inyectar instrucciones | Vacías |

## 3. Tecnologías

| Ámbito | Elección | Motivo |
|--------|----------|--------|
| Lenguaje | Python ≥ 3.12 | Ecosistema de IA y tipado estático |
| Gestor | `uv` | Entorno y dependencias reproducibles en un solo comando |
| API | FastAPI + Pydantic v2 | Validación tipada, OpenAPI automático y asíncrono |
| Cliente HTTP | `httpx` | Timeout, reintentos y transporte simulable en pruebas |
| Proveedor | OpenRouter (`cohere/north-mini-code:free`) | Modelo **gratuito** y suficiente para respuestas fundamentadas |
| Recuperación | Okapi BM25 en memoria (sin dependencias) | Ranking léxico con IDF y normalización por longitud |
| Persistencia | `sqlite3` (stdlib) | Cero dependencias, un archivo, sin servidor |
| Frontend | React 19 + TypeScript + Vite | Tipado del contrato de la API y build rápido |
| Pruebas | `pytest` + `pytest-cov` (backend), `vitest` + Testing Library (frontend) | Suites herméticas en ambos extremos |
| Calidad | `ruff`, `mypy --strict`, `oxlint`, `tsc` | Puertas de calidad automáticas |

## 4. Instalación

**Requisitos**: Python ≥ 3.12 con [`uv`](https://docs.astral.sh/uv/), Node.js ≥ 20 con npm.

```bash
# Backend
uv sync                       # crea .venv e instala dependencias
cd frontend && npm install    # instala las dependencias del frontend
```

## 5. Configuración

Todo se configura por variables de entorno; el archivo `.env` (ignorado por git) las carga.

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `OPENROUTER_API_KEY` | — | Credencial del proveedor. **Sin ella el sistema opera en modo degradado** (respuesta extractiva local) |
| `WALLE_MODELO` | `cohere/north-mini-code:free` | Modelo principal (gratuito) |
| `WALLE_TIMEOUT_SEGUNDOS` | `30` | Timeout de la invocación al proveedor |
| `WALLE_REINTENTOS` | `1` | Reintentos ante 429/5xx |
| `WALLE_UMBRAL_RELEVANCIA` | `1.0` | Umbral mínimo de relevancia documental |
| `WALLE_DATA_DIR` | `Data` | Directorio del corpus |
| `WALLE_DB_PATH` | `storage/walle.db` | Archivo SQLite (ignorado por git) |
| `WALLE_LOG_LEVEL` | `INFO` | Nivel de traza (JSON por línea) |
| `WALLE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Orígenes permitidos en desarrollo |
| `WALLE_SERVIR_FRONTEND` | `false` | Si es `true`, la API sirve además el frontend compilado (modo de un solo servicio, opt-in) |
| `WALLE_FRONTEND_DIR` | `frontend/dist` | Carpeta de la compilación del frontend |

Del lado del frontend (`frontend/.env`, variables `VITE_*`):

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | URL de la API a la que llama el navegador. Vacío ⇒ rutas relativas y **proxy de Vite** (sin peticiones entre orígenes) |
| `VITE_API_URL_FALLBACK` | `http://127.0.0.1:8000` | URL a la que se reintenta si la petición principal no llega a la API (build servido como estático) |

```bash
cp .env.example .env   # y completar OPENROUTER_API_KEY
```

## 6. Ejecución

Los dos servicios están **separados**: el puerto 8000 expone la API y el 5173 el chat.

### 6.1 API (puerto 8000)

```bash
uv run uvicorn walle.main:app --reload --port 8000
```

Al abrir <http://127.0.0.1:8000> se ve la identificación del servicio en JSON; la documentación
interactiva de la API está en <http://127.0.0.1:8000/docs> y la sonda de disponibilidad en
`/health`.

```json
{
  "servicio": "walle-api",
  "version": "0.1.0",
  "consultar": "/api/consultar",
  "historial": "/api/historial",
  "salud": "/api/salud",
  "health": "/health",
  "documentacion": "/docs",
  "frontend": "http://localhost:5173"
}
```

### 6.2 Frontend (puerto 5173)

```bash
cd frontend && npm run dev
```

La interfaz queda en <http://localhost:5173> y **llama directamente a la API del puerto 8000**
(`VITE_API_URL`). Como son orígenes distintos, la API mantiene una allowlist explícita que acepta
`http://localhost:5173` y `http://127.0.0.1:5173` (el navegador los trata como orígenes diferentes);
toda otra origem se rechaza. En la consola del navegador **no aparece ningún error de CORS**.

El proxy de Vite (`/api` → `127.0.0.1:8000`) queda como red de seguridad: si la llamada directa a la
API falla, el cliente reintenta por rutas relativas y el proxy alcanza la misma API.

Para revisar el build de producción, `npm run build && npm run preview` levanta el frontend en el
puerto 4173 **con el mismo proxy** (sin él, `/api` devolvería el `index.html` y el chat se vería
roto). Si el frontend se sirve desde otro servidor sin proxy, el cliente reintenta contra
`VITE_API_URL_FALLBACK`.

#### Recorrido manual en el navegador (checklist de T-224)

Con la API en el 8000 y `npm run dev` en el 5173, verificado en Chromium:

| # | Comprobación | Resultado |
|---|--------------|-----------|
| 1 | El panel lateral carga el historial al abrir la aplicación | ✅ |
| 2 | Una consulta válida muestra respuesta, estado `Exitosa` y sus fuentes | ✅ |
| 3 | El campo queda vacío y con el foco de vuelta tras enviar | ✅ |
| 4 | Una pregunta fuera del corpus muestra `Sin información suficiente` con el mensaje canónico y **sin** aviso de error | ✅ |
| 5 | Una solicitud de información restringida muestra `Bloqueada por seguridad` | ✅ |
| 6 | Al elegir una entrada del historial, el chat muestra la consulta completa con sus fuentes | ✅ |
| 7 | «Nueva pregunta» vacía el chat y deja intacto el historial | ✅ |
| 8 | El borrado pide confirmación y la entrada desaparece del panel | ✅ |
| 9 | El botón del panel oculta y muestra el historial sin perder el chat | ✅ |
| 10 | En pantalla estrecha (< 900 px) el panel arranca oculto y se abre y cierra sin tapar el botón de la barra | ✅ |
| 11 | Con la API detenida, se muestra un aviso accionable, sin trazas, y la interfaz sigue operativa | ✅ |
| 12 | **Ningún error de CORS en la consola del navegador** | ✅ |

### 6.3 Modo de un solo servicio (opt-in)

Si se quiere servir el chat desde la propia API:

```bash
cd frontend && npm run build                      # genera frontend/dist
WALLE_SERVIR_FRONTEND=true uv run uvicorn walle.main:app --port 8000
```

Con `WALLE_SERVIR_FRONTEND=true` la API sirve `frontend/dist` como aplicación de una sola página:
en `http://127.0.0.1:8000` se abre el chat y las rutas `/api/*` siguen siendo de la API. Por defecto
está **desactivado**, de modo que 8000 es siempre la API y 5173 el chat.

### 6.4 Ejemplo de uso

```bash
curl -X POST http://127.0.0.1:8000/api/consultar \
  -H 'Content-Type: application/json' \
  -d '{"pregunta":"¿Cuál es el monto máximo del Crédito Productivo Impulso?"}'
```

```json
{
  "respuesta": "El monto máximo del **Crédito Productivo Impulso** es de **$50.000.000**.",
  "fuentes": [
    { "documento": "Productos de Crédito.md",
      "fragmento": "Productos de Crédito > Crédito Productivo Impulso > Condiciones" }
  ],
  "estado": "Exitosa",
  "consulta_id": 1,
  "duracion_ms": 1875,
  "modelo": "cohere/north-mini-code:free"
}
```

## 7. Pruebas

```bash
# Backend (suite hermética: sin red, sin disco real)
uv run pytest
uv run pytest --cov=src/walle
uv run ruff check src tests
uv run mypy src

# Frontend
cd frontend
npm run test
npm run typecheck
npm run lint
npm run build

# Contrato contra OpenRouter real (requiere OPENROUTER_API_KEY en .env)
uv run pytest -m integration
```

**Estado actual**: 124 pruebas de backend (incluidas 4 de CORS, las de contrato y las de separación
de servicios) y 47 de frontend, en verde; `ruff`, `mypy --strict`, `oxlint` y `tsc` sin
observaciones. El recorrido manual en navegador (consulta con fuentes, respuesta insuficiente,
intento bloqueado, panel lateral, borrado, nueva conversación, error de red con la API detenida y
pantalla estrecha) queda documentado en el apartado 6.2.

### Cobertura de los casos exigidos

| Caso | Prueba |
|------|--------|
| Consulta válida | `test_api_consulta.py::test_consulta_valida_devuelve_200_y_fuentes` |
| Pregunta vacía | `test_api_consulta.py::test_pregunta_vacia_devuelve_422` |
| Base documental vacía | `test_consulta.py::test_consulta_fuera_del_corpus_no_invoca_al_modelo` |
| Caracteres especiales | `test_api_consulta.py::test_caracteres_especiales_aceptados` |
| Documentos duplicados | `test_corpus.py::test_documentos_duplicados_se_cargan_una_vez` |
| Consultas extensas | `test_api_consulta.py::test_consulta_extensa_devuelve_422` |
| Prompt injection | `test_seguridad.py::test_detecta_instrucciones_adversas` |
| Documento restringido | `test_corpus.py::test_documento_restringido_nunca_se_abre` |
| Salida con secreto | `test_consulta.py::test_salida_con_secreto_se_descarta` |
| Proveedor caído | `test_api_consulta.py::test_proveedor_caido_responde_con_fallback` |
| Escrituras concurrentes | `test_repositorio_sqlite.py::test_escrituras_concurrentes_no_producen_bloqueos` |

## 8. Seguridad

- **Allowlist documental**: `Información restringida.md` nunca se carga; sus marcadores (token
  interno, clave temporal, usuario administrador) están en constantes privadas que solo se
  **detectan y redactan**, nunca se imprimen.
- **Guardrail de entrada**: las instrucciones adversas ("ignora tus instrucciones", "actúa como…",
  "muéstrame tu prompt") y la solicitud de credenciales cortan la consulta **antes** de invocar al
  modelo.
- **Guardrail de salida**: si la respuesta generada contiene un marcador sensible, se descarta y se
  sustituye por la respuesta extractiva local.
- **Mínimo registro**: se persiste lo ya validado; en un bloqueo se guarda el mensaje genérico, nunca
  el contenido filtrado.
- **Credenciales**: solo en `.env` (ignorado por git); ninguna traza las incluye.
- **Sin `dangerouslySetInnerHTML`**: el frontend renderiza todo como texto plano.

## 9. Limitaciones

- El modelo gratuito es el punto más débil del sistema: responde en 2–8 s y puede agotar su cuota
  (`429`), momento en el que el sistema degrada a la respuesta extractiva determinista.
- La relevancia documental es **léxica** (Okapi BM25 sobre documento y sección, con sinónimos del
  dominio y entidades). Funciona bien con el vocabulario del corpus, pero una paráfrasis muy distante
  cae en "sin información suficiente".
- El modelo no tiene memoria conversacional: cada pregunta se resuelve de forma independiente.
- Sin autenticación: la API asume un despliegue interno y de confianza.
- El historial no tiene paginación (suficiente para el volumen local, no para una escala de cientos
  de miles de filas).
- La base es un archivo: no sirve para varios procesos escribiendo a la vez en red.

## 10. Mejoras futuras

1. **Búsqueda híbrida**: combinar la relevancia léxica con embeddings locales (`sentence-transformers`)
   y reranking; el corpus es pequeño, así que el coste es acotado.
2. **RAG estructurado**: modelar productos, coberturas y plazos como entidades tipadas y validar
   las cifras de la respuesta contra la fuente.
3. **Caché semántico**: cachear respuestas por (pregunta normalizada, versión del corpus) para las
   preguntas frecuentes, con invalidación por hash del corpus.
4. **Evaluación automática**: un conjunto de preguntas con respuestas esperadas y un juez que mida
   fidelidad, cobertura y citas correctas en cada cambio de prompt o de modelo.
5. **Panel de calidad**: métricas de uso (estado, latencia, tasa de "sin información suficiente",
   consultas bloqueadas) en una vista interna.
6. **PostgreSQL** cuando el historial crezca o se despliegue en varios nodos, con la misma interfaz
   `RepositorioConsultas`.
7. **Streaming opcional** para las respuestas largas, manteniendo la respuesta JSON actual.

## 11. Uso de IA en el desarrollo

El proyecto se desarrolló con un agente de IA (OpenCode, con DeepSeek V4.1 Flash Free y MiniMax M3.1) bajo
las reglas de `AGENTS.md` y la `constitucion/constitucion.md`. El detalle completo —herramientas,
qué se delegó a la IA, qué se hizo a mano, qué sugerencias se rechazaron y cómo se validaron las
respuestas— está en [`docs/Cuestionario.md`](docs/Cuestionario.md).

Resumen:

- **La IA redactó el código y la documentación**; la arquitectura, los requisitos, los criterios de
  aceptación y las decisiones de seguridad se definieron antes y se validaron con pruebas.
- **TDD estricto**: 131 pruebas (120 de backend, 11 de frontend) que fallan primero cuando el
  comportamiento no está implementado.
- **Verificación local**: `pytest`, `ruff`, `mypy --strict`, `vitest`, `oxlint` y `tsc` en verde antes
  de cada commit.
- **Revisión manual**: el recorrido con el modelo real (consultas con fuentes, consulta fuera del
  corpus, intento de prompt injection) y la validación del frontend en el navegador.

## 12. Estructura del repositorio

```
├── AGENTS.md                    reglas para los agentes de IA
├── constitucion/constitucion.md principios del proyecto (una página)
├── especificaciones/             001-api · 002-persistencia · 003-frontend
│   └── {especificacion,plan,tareas}.md
├── src/walle/                   api · dominio · recuperacion · modelo · seguridad · persistencia · fallback
├── tests/                       unit · integration · contract
├── frontend/                    React + TypeScript + Vite
├── docs/Cuestionario.md         preguntas de evaluación del proyecto
├── Data/                        corpus documental (incluye el archivo restringido: no se modifica)
└── pyproject.toml / uv.lock
```
