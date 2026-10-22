# AGENTS.md — Guía para agentes de IA

Este repositorio se desarrolla con asistencia de IA (OpenCode, Claude Code, Cursor, Copilot u otro agente equivalente). Este archivo define **cómo** debe trabajar un agente en este proyecto. Es de lectura obligatoria antes de tocar código.

> Si una instrucción de este archivo entra en conflicto con una instrucción del usuario humano en la conversación, **manda el usuario humano**. Ante la duda, pregunta.

---

## 1. Contexto del proyecto

**Walle** es un asistente interno para asesores comerciales. Responde consultas sobre créditos, microseguros, procedimientos y políticas internas **usando únicamente** la documentación de `Data/`, citando sus fuentes y sin exponer información clasificada.

Flujo: `pregunta → validación → guardrails → recuperación documental → modelo (OpenRouter) → validación de salida → respuesta + fuentes → SQLite`.

## 2. Documentos que gobiernan el trabajo

| Documento | Contenido | Cuándo leerlo |
|-----------|-----------|----------------|
| `constitucion/constitucion.md` | Principios no negociables (seguridad, calidad, TDD, IA responsable, mantenibilidad, costos, observabilidad) | **Siempre, antes de cada cambio** |
| `especificaciones/<característica>/especificacion.md` | RF, RNF, riesgos y criterios Gherkin de una característica | Antes de implementar esa característica |
| `especificaciones/<característica>/plan.md` | Arquitectura, componentes y estrategia de pruebas | Antes de implementar esa característica |
| `especificaciones/<característica>/tareas.md` | Lista ordenada de tareas técnicas | Mientras implementas |
| `docs/Cuestionario.md` | Preguntas de evaluación del proyecto | Al cierre de cada característica |

La **trazabilidad es obligatoria**: todo código nuevo debe poder rastrearse hasta un RF/RNF de una especificación.

## 3. Flujo de trabajo obligatorio

1. **No implementes sin especificación.** Si la característica no tiene `especificacion.md` aprobada, no escribas su código.
2. **TDD estricto**: primero la prueba que falla, después el mínimo código que la pasa, después refactoriza.
3. **Una característica a la vez** (`001-api` → `002-persistencia` → `003-frontend`). No mezcles cambios de características distintas en el mismo commit.
4. **Consulta al usuario humano** antes de iniciar una característica nueva, de cambiar el contrato de la API o de tomar una decisión de arquitectura no registrada.
5. **Una tarea a la vez** según el orden de `tareas.md`; marca la casilla al completarla.
6. **Verifica antes de entregar**: la suite completa, el lint y el tipado deben pasar.

## 4. Reglas de implementación

### 4.1 Seguridad (no negociable — constitución §1)

- `Data/Información restringida.md` **nunca** se carga, indexa, cita ni persiste. Vive en la lista de exclusión explícita de `src/walle/recuperacion/corpus.py`.
- Los marcadores sensibles son constantes privadas de `src/walle/seguridad/sensibles.py`. **Nunca** imprimas esos valores en logs, mensajes de error, respuestas o documentación; solo detecta y redacta.
- Toda salida del modelo se valida contra los patrones sensibles **antes** de devolverse o persistirse.
- Las credenciales solo se leen de `.env`. Nunca las escribas en el código, en los tests ni en los documentos. `.env` está en `.gitignore`: no lo modifiques para versionarlo.
- Las respuestas de error al cliente nunca incluyen trazas internas, rutas del sistema ni cuerpos de excepción.

### 4.2 IA y modelo

- El modelo por defecto es `minimax/minimax-m3.1-flash:free` (gratuito). **No** introduzcas modelos de pago ni un failover automático a ellos.
- Si el proveedor falla, se degrada a la respuesta extractiva determinista local (`src/walle/fallback/extractivo.py`), nunca a un servicio inexistente.
- **No hay chunking**: los documentos son pequeños; se envía el documento completo al modelo.
- La IA redacta; el sistema decide. Los estados válidos, los documentos permitidos y los criterios de suficiencia están en código, no en el prompt.
- Si no hay red en las pruebas, eso es un **error**: la suite debe ser hermética, con dobles de `ClienteModelo`.

### 4.3 Contrato de la API

- `POST /api/consultar` → `{pregunta}` → `{respuesta, fuentes[], estado, consulta_id, duracion_ms, modelo}`.
- Los únicos estados son: `Exitosa`, `Sin información suficiente`, `Bloqueada por seguridad`.
- El mensaje por falta de información es exactamente: `No tengo información suficiente para responder.`
- Sin streaming: respuesta JSON única.

### 4.4 Estilo y convenciones

- Python ≥ 3.12, gestor `uv` (`uv run pytest`, `uv add <dep>`, `uv sync`). No uses `pip` directamente ni crees `requirements.txt`.
- Paquete en `src/walle/`, imports absolutos (`from walle.dominio.estados import Estado`).
- Línea máxima 100. `ruff` con reglas `E,F,I,B,UP,SIM,ANN`; `mypy` estricto sobre `src/`.
- Nombres en español para el dominio y el código; en inglés solo para nombres de librerías.
- Docstrings en español, orientadas al "por qué", no al "qué".
- Comentarios en el código: explican el **por qué**, no repitan el código. Prefiere el código legible a los comentarios.
- Frontend en `frontend/` con React + npm (`npm ci`, `npm run dev`, `npm run build`). No introduzcas otro gestor de paquetes.

### 4.5 Commits

- Mensajes en español, estilo imperativo Conventional Commits: `feat(api): ...`, `fix(seguridad): ...`, `test: ...`, `docs: ...`.
- Un commit por tarea o grupo cohesivo de tareas; referencia el ID de tarea y el RF afectado: `T-020 RF-03`.
- No incluyas `.env`, bases de datos, `node_modules/` ni artefactos de build.

## 5. Comandos de verificación

```bash
uv sync                      # instalar/actualizar dependencias
uv run pytest                # suite hermética (sin red) — debe pasar
uv run pytest --cov=src/walle
uv run ruff check src tests
uv run mypy src
uv run uvicorn walle.main:app --reload     # API en http://127.0.0.1:8000
npm --prefix frontend run dev               # frontend en http://localhost:5173
```

Suite de contrato real (requiere `OPENROUTER_API_KEY` en `.env`):

```bash
uv run pytest -m integration
```

## 6. Estructura del repositorio

```
constitucion/            Principios del proyecto (una página)
especificaciones/        001-api · 002-persistencia · 003-frontend
src/walle/               api · dominio · recuperacion · modelo · seguridad · persistencia · fallback
tests/                   unit · integration · contract
frontend/                React + Vite
docs/Cuestionario.md     Preguntas de evaluación
Data/                    Corpus documental (incluye el archivo restringido: no tocar su contenido)
AGENTS.md                Este archivo
```

## 7. Qué no debes hacer

- No reescribir `Data/Información restringida.md` ni ningún otro documento de `Data/` sin autorización expresa.
- No añadir dependencias sin justificar en la constitución o en la especificación de la característica.
- No dejar `print()` en `src/`; usa el logger de `src/walle/seguridad/trazas.py`.
- No subir secretos, `.env`, `storage/*.db` ni `node_modules/`.
- No reescribir la constitución ni las especificaciones sin aprobación del usuario humano.
- No "simplificar" la lógica de guardrails para que un test pase: primero se revisa el requisito.
