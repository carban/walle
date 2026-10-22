# Cuestionario de evaluación — Walle

**Proyecto:** Asistente interno para asesores comerciales
**Stack:** Python 3.12 + FastAPI + `uv` · SQLite · React 19 + TypeScript + Vite (npm) · OpenRouter

---

## A. Uso de IA en el desarrollo

### 1. Herramientas utilizadas

| Herramienta | Uso en el proyecto |
|-------------|--------------------|
| **OpenCode** (agente de terminal) | Orquestación del desarrollo: lectura de la prueba técnica, redacción de la constitución, especificaciones, planes, tareas, código, pruebas y documentación. |
| **Claude Sonnet 4.5** | Modelo principal del agente para diseño de especificaciones, implementación del backend y refactorizaciones. |
| **MiniMax M3.1 Flash** (vía OpenRouter) | Modelo secundario del agente, usado para tareas mecánicas y para los lotes de pruebas de integración. |
| **OpenRouter API** | Proveedor del modelo de producto: `minimax/minimax-m3.1-flash:free`, gratuito. |
| **uv / pytest / ruff / mypy** | Entorno, suite de pruebas y puertas de calidad del backend. |
| **npm / Vitest / Testing Library / oxlint / tsc** | Dependencias, suite de pruebas y puertas de calidad del frontend. |
| **pdftotext** | Extracción del texto de `prueba-tecnica.pdf` (el modelo no lee PDF directamente). |

### 2. Qué actividades delegó a la IA

- **Documentación de diseño**: primer borrador de `constitucion/constitucion.md`, de las tres
  especificaciones (contexto, objetivo, alcance, RF, RNF, riesgos y criterios Gherkin), de los planes
  técnicos y de las listas de tareas.
- **Implementación**: el grueso del código de `src/walle/` (10 módulos) y de `frontend/src/`
  (8 archivos), siempre a partir de una especificación aprobada.
- **Pruebas**: los casos unitarios, de integración y de contrato, y la suite de Vitest.
- **Repetición mecánica**: refactorizados, ajustes de estilo, correcciones de tipado y de lint, y
  redacción del README y de este cuestionario.
- **Investigación**: verificación de qué modelos gratuitos existían en OpenRouter y de su
  comportamiento real (la primera opción, `gemma-4-31b-it:free`, devolvió `429` y se descartó tras
  medirlo).

### 3. Qué actividades realizó manualmente

- **Definición del problema y del alcance**: leer la prueba técnica, decidir qué hacer y qué no, y
  elegir el modelo principal (gratuito) y el modo de degradación.
- **Arquitectura y decisiones sensibles**: la allowlist documental, el orden de los guardrails
  (entrada → corpus → salida), el protocolo de persistencia y la cadena de degradación.
- **Revisión de código y de pruebas**: inspección de cada implementación contra la especificación,
  corrección de los fallos detectados y verificación de que los tests fallaban antes de la
  implementación (TDD).
- **Verificación en ejecución**: arranque de la API y del frontend, consultas reales contra
  OpenRouter, comprobación de los tres estados de respuesta, de la persistencia y del CORS.
- **Juicio de negocio**: decidir que "sin información suficiente" y "Bloqueada por seguridad" son
  estados normales y no errores, y que el documento restringido no se carga nunca.
- **Corrección de desviaciones**: cuando la IA propuso fragmentos de fuentes ilegibles ("… >
  Condiciones > …"), se corrigió la jerarquía de encabezados y el criterio de secciones relevantes.

### 4. Qué sugerencias rechazó de la IA

| Propuesta de la IA | Decisión | Motivo |
|--------------------|----------|--------|
| Añadir documentos de ejemplo a `Data/` (FAQ, tarifas, glosario) | **Rechazada** | El usuario decidió no ampliar el corpus: el conjunto entregado ya es el material de la prueba. |
| Rotar la clave de OpenRouter expuesta en `.env` | **Rechazada por ahora** | Es una recomendación válida de seguridad, pero se pospuso; `.env` está ignorado por git y la clave no se versionó. |
| Sustituir SQLite por una base cliente-servidor | **Rechazada** | El despliegue es local y monousuario; SQLite cumple sin dependencias ni operación. |
| Streaming SSE de las respuestas | **Rechazada** | El usuario decidió esperar con un indicador de carga; el contrato se mantiene como respuesta JSON única. |
| Fallback automático a un modelo de pago si el gratuito falla | **Rechazada** | Contradice el principio de costo cero y el control explícito del gasto; la degradación es local y determinista. |
| Persistir la conversación en `localStorage` | **Rechazada** | Duplicaría datos en el navegador del asesor, fuera del control de los guardrails; la fuente de verdad es SQLite. |
| Embeddings y base vectorial para el corpus | **Rechazada** | Los documentos son pequeños: se pasa el documento completo; el embedding es una mejora futura. |
| Paginación del historial desde el inicio | **Aplazada** | Sin volumen que lo justifique; se documenta como mejora futura. |

### 5. Cómo validó las respuestas de la IA

1. ** specifications primero**: ninguna implementación se escribió sin requisito, criterio de
   aceptación y tarea asociados (trazabilidad en la matriz §8 de cada especificación).
2. **TDD**: cada comportamiento se fijó primero con una prueba que fallaba; las suites quedaron en
   verde con `pytest` (117 pruebas) y `vitest` (11 pruebas).
3. **Puertas automáticas**: `ruff`, `mypy --strict`, `oxlint` y `tsc --noEmit` sin observaciones.
4. **Pruebas de contrato reales**: `uv run pytest -m integration` consulta OpenRouter de verdad y
   comprueba que la respuesta menciona la cifra correcta y trae su fuente.
5. **Revisión manual del comportamiento**: se ejecutó la API y se verificó, con el modelo real, que
   la consulta del monto máximo devuelve `$50.000.000` con la fuente correcta, que una pregunta fuera
   del corpus devuelve el mensaje canónico **sin** llamar al modelo (1 ms) y que un intento de
   prompt injection queda bloqueado sin filtrar el token.
6. **Revisión del frontend en el navegador**: recorrido de consulta, fuentes, panel lateral, borrado,
   nueva conversación y error de red con la API detenida.

---

## B. Decisiones técnicas para paso a productivo

### ¿Qué modelo utilizaría y por qué?

En producción usaría un modelo **comercial pequeño y rápido** (por ejemplo, un flash de proveedor
con precio por token bajo) en lugar del gratuito, por tres razones: SLA y cuota garantizada, mayor
consistencia en formato (JSON y citas) y latencia predecible. Mantendría el **modelo gratuito como
modo degradado explícito**, no como failover automático: si el presupuesto lo permite, el sistema
pasa al comercial; si no, degrada a la respuesta extractiva local.

El modelo no es la pieza crítica: la calidad depende del corpus y de los guardrails, no del modelo.
Por eso el diseño permite cambiar de proveedor con una variable de entorno.

### ¿Cómo optimizaría costos?

- **Caché de corpus**: los documentos se cargan una vez en memoria (ya implementado); no se releen
  por consulta.
- **Filtrado antes del modelo**: si ningún documento alcanza el umbral de relevancia, **no se llama al
  modelo** (ahorra la llamada completa y responde en ~1 ms).
- **Contexto mínimo**: se envía el documento relevante completo, no el corpus entero, y sin historial
  de la conversación.
- **Modelo gratuito por defecto** y **sin failover de pago automático**.
- **Salida corta**: el prompt limita la respuesta a 120 palabras y `max_tokens` a 700.
- **Medición**: se registra la duración y el modelo de cada consulta; con el volumen se puede decidir
  qué preguntas son candidatas a caché.

### ¿Cómo mitigaría Prompt Injection?

Con un modelo de defensa en capas, ninguna por sí sola suficiente:

1. **Separación de contextos**: el corpus documental y la pregunta del usuario se tratan como datos,
   nunca como instrucciones. El prompt de sistema declara que las instrucciones dentro de los
   documentos o de la pregunta deben ignorarse.
2. **Control de acceso al corpus (la capa más importante)**: el archivo restringido no se carga; por
   tanto, sus instrucciones **nunca llegan al modelo**. La mayoría de los ataques de prompt injection
   Explotan contenido que el modelo puede ver.
3. **Detección previa de la entrada**: patrones de instrucciones adversas y de solicitud de
   credenciales cortan la consulta antes de invocar al modelo (estado `Bloqueada por seguridad`).
4. **Validación de la salida**: la respuesta se inspecciona contra los marcadores sensibles y, si
   aparece alguno, se descarta y se sustituye por la respuesta extractiva.
5. **Mínimo privilegio y mínimo registro**: nunca se persisten ni se registran los secretos; el
   mensaje de bloqueo es genérico.
6. **Prompt de sistema versionado**: no se modifica en caliente ni depende de variables de entorno;
   vive en el repositorio y se revisa como código.

En producción añadiría además: evaluación automática de ataques (un conjunto fijo de preguntas
adversas que debe bloquearse en cada despliegue) y registro de los intentos bloqueados para detectar
patrones nuevos.

### ¿Qué guardrails implementaría?

- **Validación de entrada**: tipo, longitud mínima y máxima, y rechazo de caracteres de control.
- **Allowlist documental** y exclusión expresa del material restringido.
- **Criterio de suficiencia** medible (umbral de relevancia) y **mensaje canónico** único.
- **Tres estados cerrados**: no se puede inventar un cuarto estado.
- **Validación de salida** contra marcadores sensibles, con redacción en logs.
- **Prompts versionados** y proveedores intercambiables.
- **Restricciones de coste y de tiempo**: timeout, reintento acotado, degradación local y prohibido
  el failover a pago.
- **Red de seguridad del cliente**: React escapa por defecto y se prohíbe `dangerouslySetInnerHTML`.
- **Trazabilidad**: cada consulta deja registro con estado, fuentes y duración.

### ¿Cómo monitorearía calidad?

- **Métricas de producto**: tasa de `Exitosa` / `Sin información suficiente` / `Bloqueada por
  seguridad`; la tasa de insuficiencia es la señal más directa de cobertura del corpus.
- **Calidad de la respuesta**: un conjunto de preguntas con respuesta esperada y un juez automático
  que mida fidelidad (la cifra está en la fuente), cobertura de la pregunta y validez de la cita.
- **Calidad de las citas**: comprobar que el documento y la sección citados existen y que el fragmento
  contiene el dato afirmado.
- **Operación**: latencia (p50/p95), tasa de error del proveedor, número de degradaciones a fallback y
  duración de la escritura en base de datos.
- **Seguridad**: consultas bloqueadas, salidas descartadas por marcador sensible y cualquier coincidencia
  del escáner de secretos sobre logs y base de datos.
- **Alertas**: caída del proveedor (aumento de degradaciones), aumento Brusco de "sin información
  suficiente" (deriva del corpus) y cualquier salida marcada como sensible.

### ¿Cómo evolucionaría la solución hacia RAG?

En cuatro etapas, cada una justificada por una limitación observada:

1. **Hoy**: recuperación léxica con sinónimos del dominio + documento completo enviado al modelo. Suficiente
   porque el corpus es pequeño y el modelo puede leerlo entero.
2. **Híbrido**: añadir embeddings (locales, para no enviar el corpus a un tercero) y combinar la
   puntuación semántica con la léxica. Resuelve la paráfrasis distante.
3. **Troceado selectivo**: solo cuando los documentos crezcan; trocear por sección y recuperar los
   fragmentos más relevantes, manteniendo la cita de documento + sección.
4. **Reranking y memoria**: un reranker ligero sobre los candidatos y un registro de las consultas
   que quedaron sin respuesta para priorizar la ampliación del corpus.

En todos los pasos, la **fuente** sigue siendo obligatoria y el documento restringido sigue fuera
del índice: el RAG cambia lo que se recupera, nunca lo que se puede revelar.

---

## C. Uso de agentes

### ¿Utilizó agentes de desarrollo?

Sí. El trabajo se hizo con un agente de IA (OpenCode) que planificó, implementó, probó y documentó,
siguiendo el flujo definido en `AGENTS.md`: especificación → plan → tareas → implementación con TDD →
verificación. El repositorio incluye `AGENTS.md` con las reglas que gobiernan el trabajo de cualquier
agente (capas, convenciones, prohibiciones de seguridad, comandos de verificación).

### ¿Cómo fueron instruidos?

- Con la **constitución** como marco de referencia: seguridad por defecto, calidad, TDD, uso
  responsable de IA, mantenibilidad, optimización de costos y observabilidad.
- Con la **especificación de la característica** (RF, RNF, riesgos, criterios Gherkin) y la lista de
  tareas antes de cada bloque de trabajo.
- Con reglas explícitas: una característica a la vez, una tarea a la vez, TDD estricto, nada de
  dependencias sin justificar, nunca tocar `Data/Información restringida.md`, nunca imprimir marcadores
  sensibles, y consultar al responsable antes de cambiar el contrato de la API o la arquitectura.
- Con **criterios de aceptación verificables** en cada tarea, de modo que el agente no decidiera por
  su cuenta si algo estaba "listo".

### ¿Qué tareas delegó?

- Borradores de constitución, especificaciones, planes y listas de tareas.
- Implementación de los módulos del backend y del frontend.
- Escritura de las suites de pruebas (unitarias, de integración, de contrato y de componente).
- Refactorizados, correcciones de lint y tipado, y actualización de la documentación.

### ¿Qué tareas supervisó manualmente?

- La definición del alcance y de los criterios de aceptación.
- Todo el diseño de seguridad: allowlist, guardrails y reglas de persistencia.
- La integración con el proveedor real: elección del modelo, verificación de que la respuesta es
  correcta y de que el modo degradado funciona.
- La revisión del diff completo antes de cada commit y la ejecución manual de la aplicación.
- La validación del frontend en el navegador.

### ¿Qué decisiones no permitió tomar a la IA?

- El modelo principal (se optó por el gratuito con verificación previa del comportamiento).
- El esquema de la base de datos: se definió antes de implementar y sin `correlation_id`.
- El alcance del corpus: no se añadieron documentos a `Data/`.
- El modo de entrega (respuesta JSON única, sin streaming) y la decisión de no añadir dependencias.
- La política de coste: nunca failover automático a un modelo de pago.
- Qué se documenta y cómo se responde el cuestionario de evaluación.

---

## D. Frontera entre IA y desarrollo tradicional

### ¿Qué responsabilidades resolvería mediante desarrollo tradicional?

- **Los límites duros**: allowlist de documentos, estados válidos, mensajes canónicos, umbral de
  suficiencia, esquema de la base, validaciones de entrada y de salida.
- **La persistencia y el acceso a datos**: SQL parametrizado, transacciones, índices y versionado del
  esquema.
- **La seguridad**: detección de patrones sensibles, redacción, control de acceso y secretos.
- **La infraestructura**: despliegue, configuración, observabilidad y backups.
- **El contrato**: esquema de la API, tipos del cliente y CORS.

### ¿Qué responsabilidades delegaría a IA?

- La **redacción** de la respuesta a partir del contexto recuperado.
- La **selección** de las frases relevantes dentro de un documento.
- La **formulación** de la respuesta en lenguaje natural comprensible para el asesor.
- El **resumen** de la explicación cuando el corpus es extenso.
- La generación de **borradores de documentación y de casos de prueba** a partir de las
  especificaciones.

### ¿Qué responsabilidades nunca permitiría ejecutar a una IA?

- Decidir si una consulta se responde, se bloquea o se declara sin información suficiente.
- Autorizar acceso a material clasificado o modificar la allowlist.
- Escribir o migrar el esquema de la base de datos.
- Gestionar credenciales, rotación de claves o despliegue.
- Aprobar el paso a producción, publicar el código o tocar los datos en `Data/`.
- Modificar los guardrails de seguridad.

### ¿Cómo mantendría separadas estas responsabilidades?

- **Separación de capas**: `seguridad/`, `dominio/`, `recuperacion/` y `persistencia/` no importan nada
  del módulo del modelo; el modelo solo recibe un contexto y devuelve texto.
- **Contrato tipado**: el cliente de modelo implementa un `Protocol` (`ClienteModelo`), lo que permite
  sustituirlo por un doble en las pruebas y revisar su salida sin que el dominio dependa del
  proveedor.
- **Reglas expressed as código**: los patrones sensibles y las instrucciones adversas son
  constantes y funciones con pruebas, no instrucciones en el prompt.
- **Revisión y trazabilidad**: todo cambio del prompt es un diff revisable, y el comportamiento está
  fijado por pruebas que fallan antes de implementarse.
- **El modelo no decide el estado**: el sistema normaliza la salida (por ejemplo, si el modelo
  devuelve el mensaje canónico sin tilde, el estado se corrige) y decide el estado final.

---

## E. Optimización y operación (100.000 consultas diarias)

### ¿Qué componente tendría mayor riesgo de latencia?

**La llamada al modelo**, con diferencia: son 2–8 s por consulta con el modelo gratuito, frente a
milésimas de la recuperación y de la base de datos. En segundo lugar, el límite de cuota del proveedor
gratuito (`429`) es la causa más probable de degradación bajo carga. El segundo riesgo es la
**contención de la base** si muchas consultas escriben a la vez (mitigada ya con WAL y `busy_timeout`).

### ¿Qué estrategia utilizaría para reducir tiempos de respuesta?

1. **Caché de respuestas** por pregunta normalizada y versión del corpus (hash del contenido): las
   preguntas de los asesores son muy repetitivas.
2. **Caché de embeddings y de recuperación**: si se añade RAG semántico, el corpus indexado se
   reutiliza; hoy el corpus ya se carga una vez en memoria.
3. **Filtrado previo**: si no hay documento relevante, responder localmente sin llamar al modelo
   (ya implementado: ~1 ms frente a ~3 s).
4. **Degradación controlada**: cuando el proveedor va lento o sin cuota, el fallback extractivo
   responde en milisegundos y con la misma fuente.
5. **Conexiones reutilizadas** al proveedor (pool de `httpx`) y timeouts escalonados.
6. **Límite de concurrencia** con una cola de semáforos: ante picos, se encolan consultas en
   lugar de agotar la cuota.

### ¿Qué podría cachear?

- **Respuestas completas**, por (pregunta normalizada, hash del corpus): TTL corto y purga al
  cambiar el corpus.
- **Documentos y sus secciones**: ya se cachean en memoria al arrancar.
- **Resultados de recuperación** por pregunta normalizada.
- **Embeddings** del corpus y de las preguntas frecuentes, si se incorpora RAG semántico.
- **Consultas repetidas**: el patrón de uso real (qué se pregunta más y qué respuestas fallan) es
  además la fuente para ampliar el corpus.

### ¿Qué monitorearía?

- **Latencia**: p50, p95 y p99 por etapa (validación, guardrails, recuperación, modelo, persistencia).
- **Tasa de degradación**: porcentaje de consultas querespondieron con el fallback local; es la
  señal temprana de que el proveedor se está degradando.
- **Errores del proveedor**: 429 y 5xx por minuto; cuota restante.
- **Estado de las respuestas**: proporción de `Exitosa` / `Sin información suficiente` /
  `Bloqueada por seguridad`; un salto en la segunda indica deriva del corpus o preguntas nuevas
  repetidas.
- **Calidad**: cobertura de las preguntas frecuentes y precisión de las citas.
- **Persistencia**: tiempo de escritura, tamaño del archivo, ratio de lecturas por escritura.
- **Seguridad**: consultas bloqueadas, salidas descartadas y cualquier coincidencia del escáner de
  secretos.
- **Coste**: tokens y consultas por modelo (aunque hoy sea gratuito, es la variable a vigilar).

### ¿Cómo optimizaría costos de operación?

- Mantener el **modelo gratuito** como configuración por defecto y medir su coste real (latencia y
  tasa de error) frente a un modelo comercial pequeño antes de cambiar.
- **Caché** y filtrado previo: menos llamadas al proveedor es la palanca principal.
- **Degradación local** cuando el proveedor no responde: el fallback no cuesta tokens.
- **Sin failover automático a pago**: cualquier gasto requiere una decisión explícita.
- Coste operativo bajo: una base de datos en un archivo, sin servidor de base de datos, sin cluster y
  sin servidor de aplicación (la API sirve el frontend compilado).
- Revisar el corpus antes de salir a producción: cada documento irrelevante es contexto que se paga en tokens.

---

## F. Persistencia y gestión de datos

### ¿Qué mecanismo de almacenamiento seleccioné?

**SQLite** mediante la biblioteca estándar de Python (`sqlite3`), en un archivo local
(`storage/walle.db`), con WAL, `busy_timeout`, consultas parametrizadas y esquema versionado con
`PRAGMA user_version`.

### ¿Por qué lo seleccioné?

- **Cero dependencias y cero operación**: no hay servidor que instalar, configurar, respaldar ni
  monitorizar; el despliegue es local.
- **El volumen lo permite**: 100.000 consultas al día son unos pocos millones de filas; SQLite las
  maneja sin esfuerzo en un equipo modesto, y el historial se puede archivar por antigüedad.
- **Transaccional y duradero**: WAL y `synchronous` adecuado garantizan que una consulta confirmada por
  la API queda confirmada en disco.
- **Concurrencia suficiente**: la API escribe desde varios hilos; el modo WAL, el aislamiento por
  hilo y `busy_timeout` evitan el clásico "database is locked" (verificado con una prueba de diez
  escrituras simultáneas).
- **El acceso está encapsulado** detrás del protocolo `RepositorioConsultas`, de modo que cambiar de
  motor no obliga a reescribir la aplicación.

### ¿Qué ventajas tiene para este escenario?

- **Simplicidad operativa**: el repositorio completo son cuatro archivos.
- **Portabilidad**: el mismo código funciona en Linux, macOS y Windows, y la base se puede copiar o
  respaldar copiando un archivo.
- **Privacidad por defecto**: la base vive fuera del árbol versionado (`.gitignore`), con lo que la
  información de los asesores no llega al repositorio.
- **Coste cero de infraestructura**.
- **Consultas históricas**：el índice por fecha permite listar el historial en orden inverso sin
  recorrer toda la tabla.

---

## G. Escenario de producción

### ¿Mantendría la misma solución de persistencia?

**No en el motor, sí en el diseño.** Mantendría el **contrato** (`RepositorioConsultas`), el modelo de
datos y el esquema conceptual —son válidos para producción—, pero no el motor local.

En producción el historial pasa a ser un **activo compartido**: varios usuarios, varias instancias
de la API y necesidad de respaldos y consultas analíticas. SQLite en un archivo local no cubre eso.

### ¿Qué motor de base de datos utilizaría?

**PostgreSQL** como base del historial.

- Es el motor que mejor cubre el perfil real: acceso concurrente desde varias instancias, escritura
  sostenida, respaldosHot y consultas analíticas sobre el historial (por ejemplo, qué se pregunta más
  y qué respuestas quedan sin información suficiente).
- La migración es acotada porque el acceso ya está detrás de un protocolo: bastaría una implementación
  nueva del mismo contrato, con el mismo esquema (mismas columnas, mismos índices).
- Si la operación fuera principalmente documental y con poco crecimiento, SQLite escalado con
  réplicas de lectura sería una alternativa válida; con varias instancias de API, el sistema de
  archivos local se convierte en el cuello de botella.

### ¿Por qué?

- **Concurrencia real**: varios asesores y varias instancias escribiendo a la vez.
- **Fiabilidad operativa**: respaldos incrementales, PITR, réplicas y monitorización estándar.
- **Analítica**: el historial es la materia prima para medir calidad y decidir qué ampliar en el
  corpus; PostgreSQL permite analítica sin exportar el archivo.
- **Coste operativo bajo**: una instancia gestionada o un contenedor con volumen persistente.
- **Camino conocido**: la decisión queda detrás del protocolo, de modo que el cambio es local y
  reversible, y la migración se puede hacer por pasos (doble escritura → verificación → corte).
