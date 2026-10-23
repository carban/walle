# Cuestionario de evaluación — Walle

---

## A. Uso de IA en el desarrollo

### 1. Herramientas utilizadas

| Herramienta | Uso en el proyecto |
|-------------|--------------------|
| **OpenCode** (agente de terminal) | Desarrollo asistido: lectura de la prueba técnica, redacción de la constitución, especificaciones, planes, tareas, código, pruebas y documentación. |
| **DeepSeek V4.1** | Modelo principal del agente para diseño de especificaciones, implementación del backend, frontend y refactorizaciones. |
| **OpenRouter API** | Proveedor del modelo de producto: `cohere/north-mini-code:free`, gratuito. |
| **uv / pytest / ruff / mypy** | Entorno, suite de pruebas y puertas de calidad del backend. |
| **npm / Vitest / Testing Library / oxlint / tsc** | Dependencias, suite de pruebas y puertas de calidad del frontend. |

### 2. Qué actividades delegó a la IA

- **Documentación de diseño**: primer borrador de `constitucion/constitucion.md`, de las tres
  especificaciones (contexto, objetivo, alcance, RF, RNF, riesgos y criterios Gherkin), de los planes
  técnicos y de las listas de tareas.
- **Implementación**: el grueso del código de `src/walle/` y de `frontend/src/`, siempre a partir de una
  especificación aprobada.
- **Pruebas**: los casos unitarios, de integración y de contrato, y la suite de Vitest.
- **Repetición mecánica**: refactorizados, ajustes de estilo, correcciones de tipado y de lint, y
  borradores del README.
- **Investigación**: verificación de qué modelos gratuitos existían en OpenRouter y de su
  comportamiento real.

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

### 4. Qué sugerencias rechazó de la IA

| Propuesta de la IA | Decisión | Motivo |
|--------------------|----------|--------|
| Sustituir SQLite por una base cliente-servidor | **Rechazada** | El despliegue es local y monousuario; SQLite cumple sin dependencias ni operación. |
| Streaming SSE de las respuestas | **Rechazada** | Se decidió esperar con un indicador de carga; el contrato se mantiene como respuesta JSON única. |
| Fallback automático a un modelo de pago si el gratuito falla | **Rechazada** | Contradice el principio de coste cero y el control explícito del gasto; la degradación es local y determinista. |
| Persistir la conversación en `localStorage` | **Rechazada** | Duplicaría datos en el navegador del asesor, fuera del control de los guardrails; la fuente de verdad es SQLite. |
| Embeddings y base vectorial para el corpus | **Rechazada** | Los documentos son pequeños: se pasa el documento completo; el embedding es una mejora futura. |
| Paginación del historial desde el inicio | **Aplazada** | Sin volumen que lo justifique; se documenta como mejora futura. |

### 5. Cómo validó las respuestas de la IA

1. **Primero la especificación**: ninguna implementación se escribió sin requisito, criterio de
   aceptación y tarea asociados (trazabilidad en la matriz de cada especificación).
2. **TDD**: cada comportamiento se fijó primero con una prueba que fallaba; las suites quedaron en
   verde con `pytest` (más de 160 pruebas) y `vitest` (más de 50 casos, incluidos los e2e).
3. **Puertas automáticas**: `ruff`, `mypy --strict`, `oxlint` y `tsc --noEmit` sin observaciones.
4. **Pruebas de contrato reales**: `uv run pytest -m integration` consulta OpenRouter de verdad y
   comprueba que la respuesta menciona la cifra correcta y trae su fuente.
5. **Revisión manual del comportamiento**: se ejecutó la API y se verificó, con el modelo real, que
   por ejemplo la consulta del monto máximo devuelve `$50.000.000` con la fuente correcta, que una
   pregunta fuera del corpus devuelve el mensaje canónico **sin** llamar al modelo y que un intento de
   prompt injection queda bloqueado sin filtrar el token.
6. **Revisión del frontend en el navegador**: recorrido de consulta, fuentes, panel lateral, borrado,
   nueva conversación y error de red con la API detenida.

---

## B. Decisiones técnicas para paso a productivo

### ¿Qué modelo utilizaría y por qué?

En producción usaría un modelo **comercial pequeño y rápido**, con precio por token bajo (por ejemplo,
un Gemini 3.5 Flash), en lugar del gratuito, por tres razones: SLA y cuota garantizada, mayor consistencia
en formato (JSON y citas) y latencia predecible. Mantendría el **modelo gratuito como modo de bajo
coste seleccionable**, no como failover automático: el paso al comercial sería una decisión de
configuración y presupuesto, y si el comercial falla, el sistema degrada a la respuesta extractiva
local.

El modelo no es la pieza que más pesa: la calidad depende sobre todo del corpus y de los guardrails.
Por eso el diseño permite cambiar de proveedor con una variable de entorno.

### ¿Cómo optimizaría costos?

La optimización de costos descansa en evitar llamadas innecesarias al proveedor y minimizar el consumo de tokens en cada invocación. Por diseño, el corpus documental se carga y mantiene indexado en memoria una sola vez al arrancar el servicio, evitando operaciones repetitivas de lectura por consulta. Si la evaluación de relevancia léxica (BM25) determina que ningún documento alcanza el umbral de suficiencia, el sistema corta la ejecución y emite la respuesta canónica local en milisegundos sin invocar al modelo externo. Cuando se requiere inferencia, se inyecta únicamente el documento relevante específico —sin transferir el corpus completo ni historial conversacional prescindible—, utilizando por defecto un modelo de costo cero (`cohere/north-mini-code:free`) con prohibición expresa de failover automático a opciones de pago. Asimismo, el consumo de tokens se acota limitando contractualmente la respuesta a 120 palabras y fijando un techo de 1.200 `max_tokens`, permitiendo espacio para deliberación interna sin incurrir en desbordamiento de cuota.

### ¿Cómo mitigaría Prompt Injection?

Lo mitigaría con defensa en capas; ninguna capa basta por sí sola:

1. **Separación de contextos**: el corpus documental y la pregunta del usuario se tratan como datos,
   nunca como instrucciones. El prompt de sistema declara que las instrucciones dentro de los
   documentos o de la pregunta deben ignorarse.
2. **Control de acceso al corpus (la capa más importante)**: el archivo restringido no se carga; por
   tanto, sus instrucciones **nunca llegan al modelo**. Muchos ataques de prompt injection
   explotan contenido que el modelo puede ver.
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

La arquitectura de guardrails opera de extremo a extremo cubriendo entrada, recuperación, inferencia y salida. En la frontera de entrada, se valida estrictamente el tipo de dato, longitudes mínima y máxima, y se rechazan caracteres de control. A nivel documental y de recuperación, opera una allowlist estricta con exclusión sistemática del material clasificado, respaldada por un criterio de suficiencia medible (umbral de relevancia léxica) que activa de forma determinista el mensaje canónico único ante vacíos de información. En la orquestación, el sistema restringe el ciclo de vida a tres estados cerrados e inmutables, gestiona reintentos acotados y timeouts estrictos, y prohíbe el failover a modelos de pago recurriendo a la degradación extractiva local. En la salida, las respuestas se validan exhaustivamente contra marcadores sensibles antes de persistirse, aplicando redacción preventiva en logs. Por último, la seguridad en el cliente React delega en el escape nativo prohibiendo `dangerouslySetInnerHTML`, mientras que el subsistema de trazabilidad audita cada consulta registrando su estado, fuentes y latencia sin exponer información confidencial.

### ¿Cómo monitorearía calidad?

En un entorno productivo, el monitoreo se articularía mediante métricas e instrumentación distribuida con OpenTelemetry exportadas hacia un APM o Prometheus/Grafana. Desde la perspectiva de producto, se vigilaría la distribución de los tres estados (`Exitosa`, `Sin información suficiente` y `Bloqueada por seguridad`), donde un incremento anómalo de insuficiencia constituiría la señal primaria de desactualización o falta de cobertura del corpus. La fidelidad de las respuestas y citas se evaluaría mediante un conjunto curado de preguntas de prueba evaluadas periódicamente por un juez automatizado, verificando la presencia fáctica de las cifras y la existencia real de los documentos y secciones referenciados. Operacionalmente, se supervisaría la latencia en percentiles (p50, p95), tiempos de respuesta en milisegundos, tasas de error del proveedor (códigos 429 y 5xx), frecuencia de degradación hacia el fallback local y rendimiento de escritura en la base de datos. Por último, la observabilidad de seguridad registraría intentos de ataque bloqueados, salidas censuradas por marcadores sensibles y alertas automatizadas ante caídas de proveedores, desvíos semánticos o alertas del escáner de secretos sobre trazas y almacenamiento.

### ¿Cómo evolucionaría la solución hacia RAG?

El camino tiene cuatro etapas: la primera ya está implementada y las demás responden a limitaciones
observadas:

1. **Punto de partida (ya implementado)**: recuperación léxica con Okapi BM25 (índice por documento y
   por sección), sinónimos del dominio y documento completo enviado al modelo. Suficiente porque el
   corpus es pequeño y el modelo puede leerlo entero.
2. **Híbrido**: añadir embeddings (locales, para no enviar el corpus a un tercero) y combinar la
   puntuación semántica con la léxica. Resuelve las paráfrasis que la coincidencia de términos no
   captura.
3. **Troceado selectivo**: solo cuando los documentos crezcan; trocear por sección y recuperar los
   fragmentos más relevantes, manteniendo la cita de documento + sección.
4. **Reranking y memoria**: un reranker ligero sobre los candidatos y un registro de las consultas
   que quedaron sin respuesta para priorizar la ampliación del corpus.
5. **Búsqueda semántica para discriminar**: Analizando el comportamiento semántico se puede deducir tanto correlaciones de preguntas válidas o como preguntas que buscan vulnerar el sistema.

En todos los pasos, la **fuente** sigue siendo obligatoria y el documento restringido sigue fuera
del índice: el RAG cambia lo que se recupera, nunca lo que se puede revelar.

---

## C. Uso de agentes

### ¿Utilizó agentes de desarrollo?

Sí. Usé OpenCode como asistente durante todo el ciclo (planificación, implementación, pruebas y
documentación), pero la dirección y la validación fueron mías, siguiendo el flujo definido en
`AGENTS.md`: especificación → plan → tareas → implementación con TDD → verificación. El repositorio
incluye `AGENTS.md` con las reglas que gobiernan el trabajo de cualquier agente (capas, convenciones,
prohibiciones de seguridad, comandos de verificación).

OpenCode cubrió el alcance de este proyecto; en un equipo más grande valoraría otras herramientas,
pero para este trabajo fue suficiente. Cabe recalcar que se puedieron haber usado herramientas más avanzadas como Claude Code o Antigravity.

### ¿Cómo fueron instruidos?

Fueron instruidos bajo el marco de `AGENTS.md` y la constitución del proyecto: TDD estricto, una tarea a la vez, cero dependencias injustificadas y exclusión total de información sensible. Cada bloque de trabajo se delimitó con especificaciones previas (RF, RNF y criterios Gherkin), obligando a cumplir criterios de aceptación verificables y a consultar antes de modificar contratos o arquitectura.

### ¿Qué tareas delegó?

Delegué las tareas que podían expresarse como un requisito verificable y revisarse después:

- Los borradores de constitución, especificaciones, planes y listas de tareas, que luego corregí.
- La implementación de los módulos del backend y del frontend, siempre contra una especificación
  aprobada.
- Las suites de pruebas (unitarias, de integración, de contrato y de componente), escritas antes del
  código.
- El trabajo mecánico: refactorizados, lint, tipado y actualización de la documentación.

### ¿Qué tareas supervisó manualmente?

El criterio fue supervisar personalmente todo lo que tocara alcance, seguridad, contrato o datos:

- La definición del alcance y de los criterios de aceptación.
- El diseño de seguridad (allowlist, guardrails y reglas de persistencia) y el esquema de la base.
- La elección del modelo y la comprobación del modo degradado contra el proveedor real.
- La revisión de cada diff antes del commit y la ejecución manual de la API y del frontend.
- Algunos refactorizados que resolví directamente por rapidez.

### ¿Qué decisiones no permitió tomar a la IA?

Se restringieron por completo a la IA las decisiones estratégicas de arquitectura y de negocio, requiriendo en todo momento aprobación explícita humana. Entre ellas destacan la elección del modelo principal tras contrastar su comportamiento real, la definición y congelación del esquema de la base de datos (descartando por ejemplo identificadores de correlación al no existir llamadas distribuidas), la delimitación del corpus documental (donde la IA no pudo incorporar archivos arbitrariamente, autorizándose de forma expresa `Inversiones.md` y `Criptomoneda.md` y excluyendo el material clasificado), el modo de entrega de la API mediante respuesta JSON única sin streaming para evitar dependencias innecesarias, y la política de gasto que prohíbe de manera tajante el failover automático hacia modelos de pago.

---

## D. Frontera entre IA y desarrollo tradicional

### ¿Qué responsabilidades resolvería mediante desarrollo tradicional?

Todo control determinista, de seguridad y consistencia: los límites duros del dominio (allowlist documental, estados cerrados, mensaje canónico y validaciones de E/S), la persistencia (SQL parametrizado, transacciones ACID y esquema), la detección y redacción de datos sensibles, la observabilidad, y las reglas de infraestructura como el aislamiento de puertos (8000 API vs. 5173 frontend) con políticas estrictas de CORS y montaje opt-in (`WALLE_SERVIR_FRONTEND=true`).

### ¿Qué responsabilidades delegaría a IA?

A la inteligencia artificial se le delegan las capacidades de síntesis, razonamiento contextual y generación de lenguaje natural. Esto comprende la redacción final de la respuesta a partir del contexto recuperado de los documentos oficiales, la selección precisa de fragmentos y frases pertinentes dentro de un texto, la formulación de explicaciones claras y empáticas comprensibles para el asesor comercial, y el resumen articulado de normativas extensas. Adicionalmente, se aprovecha su capacidad generativa para producir borradores iniciales de documentación técnica y casos de prueba exhaustivos a partir de las especificaciones funcionales.

### ¿Qué responsabilidades nunca permitiría ejecutar a una IA?

Bajo ninguna circunstancia se permitiría a una IA tomar decisiones de negocio ni ejecutar operaciones de gobernanza crítica. Esto incluye decidir si una consulta se responde, se bloquea o se declara sin información suficiente (lo cual es potestad exclusiva del código de guardrails), autorizar accesos a material clasificado o alterar la allowlist documental. Tampoco se le autoriza redactar ni migrar esquemas de base de datos, gestionar credenciales o rotación de claves, aprobar despliegues a entornos productivos, alterar los datos maestros de `Data/` o relajar bajo ningún motivo los guardrails de seguridad del sistema.

### ¿Cómo mantendría separadas estas responsabilidades?

El aislamiento de responsabilidades se garantiza mediante una estricta arquitectura por capas donde `seguridad/`, `dominio/`, `recuperacion/` y `persistencia/` operan de forma independiente y sin acoplamiento hacia el módulo del modelo generativo, el cual únicamente recibe contexto y devuelve texto plano. Dicha integración se desacopla a través del contrato formal `ClienteModelo` (`Protocol`), posibilitando sustituir al proveedor por dobles en pruebas herméticas sin impactar el dominio. Adicionalmente, las defensas ante contenido sensible e inyecciones residen en constantes y funciones deterministas probadas en código y no en directivas volátiles de prompt; cualquier modificación de los prompts constituye un diff versionado en el repositorio con pruebas preexistentes; y, fundamentalmente, la asignación del estado final de negocio recae en el sistema normalizador, asegurando que la IA redacte mientras que el software decide.

---

## E. Optimización y operación (100.000 consultas diarias)

### ¿Qué componente tendría mayor riesgo de latencia?

- **La llamada al modelo (mayor riesgo con diferencia)**: son 2–8 s por consulta con el modelo gratuito, frente a milisegundos de la recuperación y de la base de datos. Este problema se puede presentar incluso con modelos de inferencia de pago.
- **Límite de cuota del proveedor (`429`)**: la causa más probable de degradación bajo carga concurrente.
- **Contención de la base de datos**: riesgo de contención si muchas consultas escriben a la vez en disco.

### ¿Qué estrategia utilizaría para reducir tiempos de respuesta?

1. **Caché de respuestas** por pregunta normalizada y versión del corpus (hash del contenido): las preguntas de los asesores suelen repetirse mucho.
2. **Caché de embeddings y de recuperación**: si se añade RAG semántico, el corpus indexado se reutiliza; hoy el corpus ya se carga una vez en memoria.
3. **Filtrado previo**: si no hay documento relevante, responder localmente sin llamar al modelo (ya implementado: ~1 ms frente a ~3 s).
4. **Degradación controlada**: cuando el proveedor va lento o sin cuota, el fallback extractivo responde en milisegundos y con la misma fuente.
5. **Reutilizar el cliente HTTP** del proveedor (hoy se abre uno por llamada) y escalonar los timeouts.
6. **Límite de concurrencia**: peticiones por minuto y objetivo de throughput.

### ¿Qué podría cachear?

- **Respuestas completas**, por (pregunta normalizada, hash del corpus): TTL corto y purga al cambiar el corpus.
- **Documentos y sus secciones**: ya se cachean en memoria al arrancar.
- **Resultados de recuperación** por pregunta normalizada.
- **Embeddings** del corpus y de las preguntas frecuentes, si se incorpora RAG semántico.
- **Consultas repetidas**: el patrón de uso real (qué se pregunta más y qué respuestas fallan) es además la fuente para ampliar el corpus.

### ¿Qué monitorearía?

- **Latencia y tiempos de respuesta**: p50, p95 y p99 por etapa (validación, guardrails, recuperación, modelo, persistencia y logs).
- **Tasa de degradación**: porcentaje de consultas que respondieron con el fallback local; es la señal temprana de que el proveedor se está degradando.
- **Errores del proveedor**: tasa de 429/5xx y reintentos en los logs.
- **Estado de las respuestas**: proporción de `Exitosa` / `Sin información suficiente` / `Bloqueada por seguridad`; un salto en la segunda indica deriva del corpus o preguntas nuevas repetidas.
- **Calidad**: cobertura de las preguntas frecuentes y precisión de las citas.
- **Persistencia**: tiempo de escritura, tamaño del archivo, ratio de lecturas por escritura.
- **Seguridad**: consultas bloqueadas, salidas descartadas y cualquier coincidencia del escáner de secretos.
- **Coste**: tokens y consultas por modelo (aunque hoy sea gratuito, es la variable a vigilar).

### ¿Cómo optimizaría costos de operación?

- Mantener el **modelo gratuito** como configuración por defecto y medir su coste real (latencia y tasa de error) frente a un modelo comercial pequeño antes de cambiar.
- **Caché** y filtrado previo: menos llamadas al proveedor es la palanca principal.
- **Degradación local** cuando el proveedor no responde: el fallback no cuesta tokens.
- **Sin failover automático a pago**: cualquier gasto requiere una decisión explícita.
- Coste operativo bajo: una base de datos en un archivo, sin servidor de base de datos ni cluster, y un único proceso de API más un frontend estático.
- Revisar el corpus antes de salir a producción: cada documento irrelevante ensucia la recuperación y puede desplazar al documento correcto.

---

## F. Persistencia y gestión de datos

### ¿Qué mecanismo de almacenamiento seleccioné?

**SQLite** mediante la biblioteca estándar de Python (`sqlite3`), en un archivo local
(`storage/walle.db`), con WAL, `busy_timeout`, consultas parametrizadas y esquema versionado con
`PRAGMA user_version`.

### ¿Por qué lo seleccioné?

Por su nula sobrecarga operativa en un despliegue local y monousuario, sin servidores que administrar. Maneja holgadamente una alta carga proyectada de varios requests por minuto con durabilidad transaccional mediante WAL y aislamiento multihilo con `busy_timeout` (verificado con hilos simultáneos). Además, queda desacoplado tras `RepositorioConsultas`, facilitando migrar a otro motor en producción sin alterar la aplicación.

### ¿Qué ventajas tiene para este escenario?

Para este escenario específico, SQLite aporta una simplicidad operativa insuperable al residir toda la persistencia en un único archivo local, facilitando copias de respaldo y portabilidad inmediata entre cualquier sistema operativo sin requerir administración de infraestructura. A su vez, garantiza privacidad por diseño al mantener los datos de las consultas de los asesores fuera del control de versiones (`.gitignore`), todo ello con costo cero de infraestructura y aprovechando las librerías nativas del lenguaje sin dependencias externas adicionales.

---

## G. Escenario de producción

### ¿Mantendría la misma solución de persistencia?

**No en el motor, sí en el diseño.** Mantendría el **contrato** (`RepositorioConsultas`), el modelo
de datos y el esquema conceptual —son válidos para producción—, pero no el motor local.

En producción el historial pasa a ser un **activo compartido**: varios usuarios, varias instancias
de la API y necesidad de respaldos y consultas analíticas. SQLite en un archivo local no cubre eso.

### ¿Qué motor de base de datos utilizaría?

En un entorno de producción distribuido se utilizaría **PostgreSQL** como base del historial. PostgreSQL cubre de manera óptima el perfil transaccional de un entorno con múltiples instancias de API escribiendo concurrentemente de forma sostenida, proporcionando respaldos en caliente y capacidades nativas de analítica sobre el historial (fundamentales para auditar qué consultas fallan o quedan sin información suficiente). La migración resulta técnicamente directa y de bajo riesgo gracias a que la capa de persistencia está encapsulada tras el protocolo `RepositorioConsultas`, permitiendo desplegar una nueva implementación que conserve idéntico esquema, columnas e índices. Si bien arquitecturas como SQLite con LiteFS o rqlite son viables para cargas predominantemente de lectura, el escalado horizontal de la API convierte al sistema de archivos local en un cuello de botella para la escritura concurrente.

### ¿Por qué?

La elección de PostgreSQL se fundamenta en su capacidad de soportar concurrencia real con múltiples asesores e instancias escribiendo en simultáneo, respaldada por una robusta fiabilidad operativa que incluye respaldos incrementales, recuperación punto en el tiempo (PITR), réplicas de lectura y herramientas estándar de monitoreo. Además, habilita la explotación analítica directa del historial sin necesidad de exportar datos, permitiendo retroalimentar la calidad de las respuestas y detectar vacíos en el corpus documental. Todo ello se logra con un costo operativo predecible (mediante instancias gestionadas en la nube o contenedores con volúmenes persistentes) y siguiendo un proceso de migración de bajo riesgo, estructurado y reversible en etapas gracias al desacoplamiento de la interfaz (doble escritura, verificación y corte definitivo).
