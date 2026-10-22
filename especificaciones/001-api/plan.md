# Plan 001 — API de consultas

**Característica:** API REST del asistente Walle
**Versión:** 1.0 · Estado: para revisión
**Especificación:** `especificaciones/001-api/especificacion.md`
**Tareas:** `especificaciones/001-api/tareas.md`

---

## 1. Arquitectura propuesta

```
                    ┌──────────────────────────────────────────┐
   Cliente HTTP ───▶│            FastAPI (capa api)           │
   (React / curl)   │  POST /api/consultar · GET /api/salud    │
                    │  Pydantic: validación tipada de entrada  │
                    └───────────────┬──────────────────────────┘
                                    │ Consulta(validada)
                    ┌───────────────▼──────────────────────────┐
                    │      Orquestador de consultas            │
                    │  (capa dominio: consulta.py)              │
                    └──┬───────────────┬───────────────┬───────┘
                       │               │               │
      ┌────────────────▼───┐   ┌───────▼────────┐  ┌───▼───────────────┐
      │  Guardrails        │   │  Recuperación  │  │  Cliente de       │
      │  (capa seguridad)  │   │  documental    │  │  modelo           │
      │  · allowlist docs  │   │  (capas doc)   │  │  (OpenRouter)     │
      │  · anti-inyección  │   │  sin troceado  │  │  · timeout        │
      │  · saneo de salida │   │  · umbral      │  │  · reintento      │
      └────────┬───────────┘   └───────┬────────┘  └───┬───────────────┘
               │                       │               │
               ▼                       ▼               ▼
        Bloqueada por         Contexto con        free model
        seguridad            documento(s)        minimax + fallback
                                                        │
                    ┌───────────────────────────────────▼──────────────┐
                    │  Persistencia (capa persistencia)                │
                    │  Hook de registro → SQLite  [char. 002]          │
                    └──────────────────────────────────────────────────┘
```

### 1.1 Principio de flujo

```
pregunta
   │
   ├─(1) validación de entrada            → 422 si es inválida
   │
   ├─(2) guardrail anti-inyección         → 200 "Bloqueada por seguridad" (sin llamar al modelo)
   │
   ├─(3) recuperación: relevancia de docs → si ninguno supera el umbral:
   │                                        → 200 "Sin información suficiente" (sin llamar al modelo)
   │
   ├─(4) llamada al modelo con el documento completo
   │        ├─ ok         → (5) saneo/validación de salida
   │        └─ excepción  → fallback determinista (extracción del documento)
   │
   ├─(5) validación de salida             → si contiene patrón sensible: se descarta
   │                                        y se responde con el mensaje canónico
   │
   └─(6) respuesta 200 {respuesta, fuentes, estado, ...}
            + registro en persistencia (característica 002)
```

### 1.2 Sin troceado (chunking)

Los seis documentos del corpus son pequeños (decenas de líneas). Trocearlos no aporta precisión y complica la trazabilidad de las fuentes. El sistema:

1. Carga cada documento permitido completo en memoria, una vez al arrancar, con su hash de contenido para detectar duplicados.
2. Ante cada pregunta calcula un puntaje de relevancia léxico (tokenización con normalización de acentos y minúsculas + tabla de sinónimos del dominio + solapamiento de phrasesbigramas).
3. Selecciona el **documento más relevante**; además incluye los documentos que alcanzan un **30 % del mejor puntaje**, de modo que una pregunta que cruza dos dominios (un seguro y un crédito) llegue al modelo con ambos documentos.
4. Envía el **documento completo** (o los documentos seleccionados) al modelo.

## 2. Componentes

### 2.1 Estructura de directorios

```
src/
└── walle/
    ├── __init__.py
    ├── main.py                 # fábrica de la app FastAPI, CORS, routers, StaticFiles (frontend)
    ├── config.py               # Settings (pydantic-settings): .env, modelo, timeouts, rutas
    ├── api/
    │   ├── __init__.py
    │   ├── esquema.py           # modelos Pydantic: ConsultaRequest, ConsultaResponse, Fuente, Estado
    │   └── rutas.py            # POST /api/consultar, GET /api/salud, GET /api/documentos
    ├── dominio/
    │   ├── __init__.py
    │   ├── consulta.py         # orquestador: valida → guardrails → recupera → responde
    │   └── estados.py          # Enum Estado (Exitosa | Sin información suficiente | Bloqueada por seguridad)
    ├── recuperacion/
    │   ├── __init__.py
    │   ├── corpus.py           # carga Data/, allowlist, hash/dedupe, cache en memoria
    │   ├── relevance.py        # tokenización, sinónimos, puntaje, umbral, selección
    │   └── fuentes.py          # construcción de la lista de fuentes (documento + fragmento)
    ├── modelo/
    │   ├── __init__.py
    │   ├── cliente.py          # interfaz ClienteModelo + ClienteOpenRouter (httpx)
    │   └── prompt.py           # prompt de sistema, plantilla de usuario, contrato de salida
    ├── seguridad/
    │   ├── __init__.py
    │   ├── inyeccion.py        # detección de intentos de inyección/extracción
    │   ├── sensibles.py        # patrones de información sensible, redacción, saneo de salida
    │   └── trazas.py           # logging estructurado con correlation_id, redacción
    ├── persistencia/
    │   ├── __init__.py
    │   └── repositorio.py      # protocolo + implementación SQLite (char. 002)
    └── fallback/
        ├── __init__.py
        └── extractivo.py       # respuesta determinista cuando el proveedor falla
tests/
├── unit/                      # herméticos, sin red
├── integration/               # FastAPI TestClient, proveedor simulado
└── contract/                  # smoke test contra OpenRouter real (opt-in)
```

### 2.2 Contratos principales

**Entrada**

```json
{ "pregunta": "¿Cuál es el monto máximo del Crédito Productivo Impulso?" }
```

**Salida exitosa**

```json
{
  "respuesta": "El monto máximo del Crédito Productivo Impulso es de $50.000.000.",
  "fuentes": [
    { "documento": "Productos de Crédito.md", "fragmento": "Crédito Productivo Impulso > Condiciones" }
  ],
  "estado": "Exitosa",
  "consulta_id": 12,
  "duracion_ms": 8431,
  "modelo": "cohere/north-mini-code:free"
}
```

**Salida sin información suficiente**

```json
{
  "respuesta": "No tengo información suficiente para responder.",
  "fuentes": [],
  "estado": "Sin información suficiente",
  "consulta_id": 13,
  "duracion_ms": 21,
  "modelo": null
}
```

**Salida bloqueada**

```json
{
  "respuesta": "No puedo compartir información clasificada ni seguir instrucciones ajenas al sistema.",
  "fuentes": [],
  "estado": "Bloqueada por seguridad",
  "consulta_id": 14,
  "duracion_ms": 3,
  "modelo": null
}
```

**Error de validación (422)** — cuerpo estándar de FastAPI, con el campo `pregunta` señalado y sin eco del cuerpo recibido.

### 2.3 Recuperación documental

- **Allowlist** (`config.py`): por defecto se permiten `Manual del Asesor Comercial.md`, `Políticas de Atención.md`, `Portafolio de Microseguros.md`, `Procedimientos Operativos.md`, `Productos de Crédito.md`. `Información restringida.md` queda en la lista de exclusión explícita y **nunca** se carga.
- **Deduplicación**: hash SHA-256 del contenido normalizado; dos archivos con el mismo contenido se cargan una sola vez y se reporta el duplicado en la traza.
- **Puntaje de relevancia**: para cada documento se calcula la cobertura de términos de la pregunta (normalizados, sin acentos, con sinónimos del dominio: `microseguro ↔ seguro`, `plazo ↔ meses`, `monto ↔ límite`, `reclamación ↔ reclamación`) más un bonus por coincidencia de entidades (nombres de producto, `$`, porcentajes). Si el puntaje máximo es inferior al **umbral 1.0** (ningún término de la pregunta coincide), no hay documento relevante.
- **Fuentes**: cada documento se parsea por secciones (`#`, `##`, `###`); la fuente apunta al encabezado de la sección usada.

### 2.4 Guardrails

| Capa | Control | Resultado |
|------|---------|-----------|
| Entrada | Detección de instrucciones adversas (`ignora tus instrucciones`, `actúa como`, `revela`, `token`, `clave`, `credencial`, `administrador`, `system prompt`) combinadas con intención de obtener material interno | `Bloqueada por seguridad`, sin invocar al modelo |
| Corpus | Allowlist; el documento restringido no se carga ni se cita | Sin fuga por contexto |
| Salida | Búsqueda de marcadores sensibles (`INT-8457-SECRET-782`, `TMP-998877`, `admin_laboratorio`, `LAB-W-CORE` y patrones genéricos de token/clave) | Se descarta la salida y se responde con el mensaje canónico |
| Logs | Redacción de secretos y del cuerpo de las excepciones | Sin secretos en trazas |

> Nota: los valores literales de los marcadores sensibles viven en el código como constantes privadas de `seguridad/sensibles.py`; no se imprimen en logs ni en las respuestas de error.

### 2.5 Cliente de modelo

- Interfaz `ClienteModelo` con un único método `responder(contexto: list[Documento], pregunta: str) -> str`. Permite sustituirlo por un doble en las pruebas.
- `ClienteOpenRouter`: HTTP `POST https://openrouter.ai/api/v1/chat/completions`, `temperature=0.1`, `timeout=30 s`, un reintento con espera exponencial corta ante 429/5xx.
- **Cadena de degradación**: modelo configurado (gratuito) → sin proveedor disponible → respuesta extractiva determinista. El failover a modelos de pago está prohibido por la constitución.
- **Fallback extractivo**: extrae del documento las frases con mayor solapamiento con la pregunta y arma una respuesta breve con las frases y la referencia a la sección; si no hay solapamiento, devuelve el mensaje canónico.

### 2.6 Configuración

Variables en `.env` (con valores por defecto seguros en `config.py`):

| Variable | Por defecto | Uso |
|----------|-------------|-----|
| `OPENROUTER_API_KEY` | — | Credencial del proveedor; si falta, el sistema opera en modo fallback |
| `WALLE_MODELO` | `cohere/north-mini-code:free` | Modelo principal (gratuito) |
| `WALLE_TIMEOUT_SEGUNDOS` | `30` | Timeout de la invocación al proveedor |
| `WALLE_REINTENTOS` | `1` | Reintentos ante 429/5xx |
| `WALLE_UMBRAL_RELEVANCIA` | `1.0` | Umbral mínimo de relevancia documental |
| `WALLE_DATA_DIR` | `Data` | Directorio del corpus |
| `WALLE_DB_PATH` | `storage/walle.db` | Ruta de SQLite (característica 002) |
| `WALLE_LOG_LEVEL` | `INFO` | Nivel de traza |
| `WALLE_CORS_ORIGINS` | `http://localhost:5173` | Orígenes permitidos para el dev server de Vite |

### 2.7 Observabilidad

- `correlation_id` por consulta (UUID4 corto), devuelto en la cabecera `X-Correlation-ID` y en las trazas; `consulta_id` es el identificador que asigna la persistencia (característica 002).
- Trazas estructuradas (JSON) por etapa: `validacion`, `guardrail`, `recuperacion`, `modelo`, `persistencia`, con duración y resultado.
- `GET /api/salud` → `{estado, corpus: {documentos, duplicados}, proveedor: {modelo, disponible}, version}`.

## 3. Estrategia de pruebas

### 3.1 Principios

- **Hermeticidad**: la suite por defecto no sale a la red. El cliente de modelo se sustituye por un doble; el reloj y el identificador de correlación se inyectan.
- **TDD estricto**: cada tarea de `tareas.md` empieza por una prueba que falla.
- **Niveles**:
  - `tests/unit/` — funciones puras: validación, relevancia, guardrails, estados, fallback, fuentes.
  - `tests/integration/` — la app FastAPI completa con `TestClient` y proveedor simulado; se validan los códigos HTTP y el contrato JSON.
  - `tests/contract/` — opcional, contra OpenRouter real; se marca `@pytest.mark.integration` y se ejecuta solo con `--integration` y `OPENROUTER_API_KEY` presente.

### 3.2 Matriz de casos exigidos por el enunciado

| Caso | Tipo | Prueba |
|------|------|--------|
| Consulta válida | Positivo | `test_consulta_valida_devuelve_200_y_fuentes` |
| Pregunta vacía | Negativo | `test_pregunta_vacia_422` |
| Base documental vacía | Negativo | `test_corpus_vacio_responde_sin_informacion` |
| Caracteres especiales | Borde | `test_caracteres_especiales_aceptados` |
| Documentos duplicados | Borde | `test_documentos_duplicados_se_cargan_una_vez` |
| Consultas extensas | Borde | `test_consulta_extensa_422` |
| Prompt injection | Seguridad | `test_intento_inyeccion_bloqueado` |
| Documento restringido | Seguridad | `test_documento_restringido_no_se_carga` |
| Salida con secreto | Seguridad | `test_salida_con_token_se_descarta` |
| Proveedor caído | Degradación | `test_proveedor_caido_usa_fallback` |
| Sin invocar al modelo | Costo | `test_fuera_de_corpus_no_invoca_modelo` |
| Persistencia | Integración | `test_consulta_se_persiste` (char. 002) |

### 3.3 Comandos

```bash
uv run pytest                      # suite hermética
uv run pytest --cov=src/walle      # con cobertura
uv run pytest -m integration       # solo contrato real (requiere OPENROUTER_API_KEY)
uv run ruff check src tests         # lint
uv run mypy src                     # tipado
```

## 4. Riesgos de implementación y mitigación

| Riesgo | Mitigación en el plan |
|--------|-----------------------|
| Los modelos gratuitos devuelven 429 con frecuencia | Timeout + reintento acotado + fallback determinista; nunca pago automático |
| La relevancia léxica falla con paráfrasis | Sinónimos del dominio + entidades + umbral conservador que prefiere responder "sin información suficiente" |
| Fuga por el documento restringido | Allowlist en configuración, cargada al inicio y verificada por prueba unitaria |
| Dependencia de red en las pruebas | Dobles de `ClienteModelo`; la suite por defecto no hace peticiones HTTP |
| Latencia alta (~8 s observadas) | Sin streaming (decisión D-02); el frontend muestra estado de carga y el tiempo se mide y se registra |
