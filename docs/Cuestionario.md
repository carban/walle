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

La delegación a la IA se concentró en tareas con requisitos formalmente verificables. En la fase de diseño, se le encomendó la redacción de los primeros borradores de la constitución (`constitucion/constitucion.md`), las tres especificaciones técnicas (contexto, objetivo, alcance, RF, RNF, riesgos y criterios Gherkin), los planes arquitectónicos y las listas de tareas. En la fase de construcción, generó el grueso del código en `src/walle/` y `frontend/src/` siempre a partir de especificaciones aprobadas, así como la suite completa de pruebas (unitarias, integración, contrato y pruebas de componentes en Vitest). Asimismo, se delegaron actividades mecánicas e iterativas como refactorizaciones, ajustes de estilo, resolución de observaciones de tipado y linter, borradores de documentación y la investigación preliminar sobre la disponibilidad y comportamiento de modelos gratuitos en OpenRouter.

### 3. Qué actividades realizó manualmente

La intervención manual se reservó para la dirección técnica, el juicio de negocio y el control estricto de calidad y seguridad. Esto incluyó la definición inicial del problema y del alcance a partir de la prueba técnica, la selección del modelo gratuito y el diseño del modo degradado determinista. En el plano arquitectónico, se fijaron manualmente la allowlist documental, el orden de evaluación de los guardrails (entrada → corpus → salida), el protocolo de persistencia y la cadena de degradación. Del mismo modo, se realizó la supervisión rigurosa de cada diff contra la especificación, garantizando la aplicación estricta de TDD (comprobando que los tests fallaran antes de codificar). Finalmente, se ejecutó la validación manual de extremo a extremo (arranque de la API en el puerto 8000 y del frontend en el 5173, pruebas de CORS, verificación de los tres estados de respuesta y confirmación en disco) y se tomaron las decisiones críticas de negocio, tales como tratar "sin información suficiente" y "Bloqueada por seguridad" como estados normales de operación y asegurar la exclusión absoluta del documento restringido.

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

La instrucción del agente se articuló mediante un marco de gobierno jerárquico fijado en `AGENTS.md` y en la constitución del proyecto (seguridad por defecto, calidad, TDD, uso responsable de IA, mantenibilidad, costos y observabilidad). El agente operó bajo directrices explícitas y no negociables: abordar una sola característica y tarea técnica a la vez, ejecutar TDD riguroso, no añadir dependencias externas sin justificación y respetar de forma absoluta las restricciones de seguridad (como la exclusión total de `Data/Información restringida.md` y la no revelación de marcadores sensibles). Antes de cada bloque de implementación, se le alimentó con la especificación técnica correspondiente (abarcando requisitos funcionales, no funcionales, análisis de riesgos y criterios Gherkin), garantizando que su trabajo estuviese delimitado por criterios de aceptación verificables mediante pruebas automatizadas y requiriendo siempre la intervención humana ante modificaciones de arquitectura o contratos de API.

### ¿Qué tareas delegó?

Se delegaron aquellas actividades susceptibles de expresarse como un requisito formalmente verificable y auditable. Esto incluyó la redacción inicial de borradores de la constitución, especificaciones funcionales, planes técnicos y listas de tareas, sujetos siempre a posterior corrección y aprobación humana. Asimismo, se delegó la implementación modular del código tanto en backend como en frontend contra especificaciones aprobadas, la generación previa de las suites de pruebas automatizadas (unitarias, integración, contrato y componentes en Vitest) y la ejecución de tareas mecánicas tales como refactorizaciones de estilo, resolución de avisos de tipado estricto y linter, y la actualización de la documentación técnica.

### ¿Qué tareas supervisó manualmente?

La supervisión manual se concentró de forma estricta en todo componente que afectara el alcance del proyecto, la seguridad, los contratos de interfaz o los datos sensibles. Se definió y acotó personalmente el alcance y los criterios de aceptación, el diseño de la arquitectura de seguridad (allowlist documental, guardrails y reglas de persistencia) y el esquema relacional de la base de datos. De igual forma, se evaluó la selección del modelo gratuito comprobando su comportamiento frente al modo degradado local, se inspeccionó minuciosamente cada diff antes de autorizar los commits, se ejecutaron pruebas operativas manuales de la API y del frontend en el navegador, y se resolvieron directamente refactorizaciones puntuales cuando la rapidez técnica lo aconsejaba.

### ¿Qué decisiones no permitió tomar a la IA?

Se restringieron por completo a la IA las decisiones estratégicas de arquitectura y de negocio, requiriendo en todo momento aprobación explícita humana. Entre ellas destacan la elección del modelo principal tras contrastar su comportamiento real, la definición y congelación del esquema de la base de datos (descartando por ejemplo identificadores de correlación al no existir llamadas distribuidas), la delimitación del corpus documental (donde la IA no pudo incorporar archivos arbitrariamente, autorizándose de forma expresa `Inversiones.md` y `Criptomoneda.md` y excluyendo el material clasificado), el modo de entrega de la API mediante respuesta JSON única sin streaming para evitar dependencias innecesarias, y la política de gasto que prohíbe de manera tajante el failover automático hacia modelos de pago.

---

## D. Frontera entre IA y desarrollo tradicional

### ¿Qué responsabilidades resolvería mediante desarrollo tradicional?

El desarrollo determinista tradicional asume el control estricto de todas las fronteras críticas, la seguridad y la consistencia del sistema. Esto abarca la definición de límites duros del dominio —como la allowlist documental, los estados de respuesta cerrados, el mensaje canónico de falta de información, los esquemas de validación de entrada/salida y el umbral de corte de suficiencia léxica—. De igual forma, la persistencia de datos (SQL parametrizado, transacciones ACID, índices y migraciones de esquema), la infraestructura, la observabilidad y los mecanismos de seguridad (escaneo y redacción de marcadores sensibles, aislamiento de secretos y reglas de acceso) se implementan íntegramente en código. Asimismo, el desacoplamiento operativo entre la API (puerto 8000) y la interfaz de usuario (puerto 5173), gobernado por políticas estrictas de CORS y montaje opt-in (`WALLE_SERVIR_FRONTEND=true`), permanece como una responsabilidad clásica de ingeniería donde la IA no tiene injerencia decisoria.

### ¿Qué responsabilidades delegaría a IA?

A la inteligencia artificial se le delegan las capacidades de síntesis, razonamiento contextual y generación de lenguaje natural. Esto comprende la redacción final de la respuesta a partir del contexto recuperado de los documentos oficiales, la selección precisa de fragmentos y frases pertinentes dentro de un texto, la formulación de explicaciones claras y empáticas comprensibles para el asesor comercial, y el resumen articulado de normativas extensas. Adicionalmente, se aprovecha su capacidad generativa para producir borradores iniciales de documentación técnica y casos de prueba exhaustivos a partir de las especificaciones funcionales.

### ¿Qué responsabilidades nunca permitiría ejecutar a una IA?

Bajo ninguna circunstancia se permitiría a una IA tomar decisiones de negocio ni ejecutar operaciones de gobernanza crítica. Esto incluye decidir si una consulta se responde, se bloquea o se declara sin información suficiente (lo cual es potestad exclusiva del código de guardrails), autorizar accesos a material clasificado o alterar la allowlist documental. Tampoco se le autoriza redactar ni migrar esquemas de base de datos, gestionar credenciales o rotación de claves, aprobar despliegues a entornos productivos, alterar los datos maestros de `Data/` o relajar bajo ningún motivo los guardrails de seguridad del sistema.

### ¿Cómo mantendría separadas estas responsabilidades?

El aislamiento de responsabilidades se garantiza mediante una estricta arquitectura por capas donde `seguridad/`, `dominio/`, `recuperacion/` y `persistencia/` operan de forma independiente y sin acoplamiento hacia el módulo del modelo generativo, el cual únicamente recibe contexto y devuelve texto plano. Dicha integración se desacopla a través del contrato formal `ClienteModelo` (`Protocol`), posibilitando sustituir al proveedor por dobles en pruebas herméticas sin impactar el dominio. Adicionalmente, las defensas ante contenido sensible e inyecciones residen en constantes y funciones deterministas probadas en código y no en directivas volátiles de prompt; cualquier modificación de los prompts constituye un diff versionado en el repositorio con pruebas preexistentes; y, fundamentalmente, la asignación del estado final de negocio recae en el sistema normalizador, asegurando que la IA redacte mientras que el software decide.

---

## E. Optimización y operación (100.000 consultas diarias)

### ¿Qué componente tendría mayor riesgo de latencia?

**La llamada al modelo**, con diferencia: son 2–8 s por consulta con el modelo gratuito, frente a
milisegundos de la recuperación y de la base de datos. Después aparece el límite de cuota del
proveedor gratuito (`429`), la causa más probable de degradación bajo carga, y la **contención de la
base** si muchas consultas escriben a la vez. 

Este problema se puede presentar incluso con modelos de inferencia de pago.

### ¿Qué estrategia utilizaría para reducir tiempos de respuesta?

Para amortiguar la latencia de inferencia y optimizar el rendimiento bajo alta concurrencia, implementaría una estrategia basada en almacenamiento en caché jerárquico, corte temprano de peticiones y optimización de conexiones. En primer lugar, se aplicaría una caché de respuestas finales indexada por la normalización de la pregunta y el hash de versión del corpus, aprovechando la alta repetición en las dudas de los asesores. A nivel de recuperación, se reutilizarían los índices y embeddings en memoria (el corpus ya se mantiene precargado hoy en día). En segundo lugar, se maximiza el filtrado previo determinista: si la consulta carece de relevancia documental, se responde localmente en ~1 ms sin incurrir en los ~3 segundos de la llamada externa. En tercer lugar, ante cuellos de botella o agotamiento de cuota, la degradación controlada hacia el fallback extractivo resuelve la petición en milisegundos garantizando la fuente. Finalmente, en la capa de transporte se reutilizaría una sesión HTTP persistente con el proveedor (evitando abrir un cliente por llamada), escalonando los timeouts y definiendo techos de concurrencia y peticiones por minuto para proteger el throughput del sistema.

### ¿Qué podría cachear?

El esquema de almacenamiento en caché se estructuraría en múltiples niveles complementarios: respuestas completas asociadas a la tupla de pregunta normalizada y hash del corpus (con un TTL corto e invalidación automática ante actualizaciones documentales), los documentos oficiales y sus secciones estructuradas (actualmente precargados en memoria al iniciar la aplicación) y los resultados intermedios de recuperación léxica. De incorporarse RAG semántico en el futuro, se cachearían adicionalmente los embeddings del corpus y de las preguntas frecuentes. Por último, registrar y cachear las consultas repetidas no solo acelera la respuesta, sino que proporciona telemetría sobre los patrones reales de uso para guiar la ampliación del acervo documental.

### ¿Qué monitorearía?

El sistema de observabilidad supervisaría integralmente métricas de rendimiento, fiabilidad, calidad y seguridad. En el ámbito operativo, se medirían las latencias en percentiles (p50, p95 y p99) desglosadas por etapa (validación, guardrails, recuperación, modelo y persistencia), los tiempos de respuesta en milisegundos, las tasas de error del proveedor (códigos 429 y 5xx), los reintentos y la tasa de degradación hacia el fallback local, cuya elevación alerta prematuramente sobre fallos del modelo externo. A nivel de producto y calidad, se vigilaría la proporción entre los estados `Exitosa`, `Sin información suficiente` (señal clave de deriva del corpus) y `Bloqueada por seguridad`, junto con la precisión de las citas y la cobertura de respuestas esperadas. Asimismo, en la capa de persistencia se auditaría el tiempo de escritura, tamaño de base de datos y ratio de lecturas frente a escrituras; en seguridad, el volumen de consultas bloqueadas, salidas censuradas y alertas del escáner de secretos; y en costos, el consumo granular de tokens y llamadas por modelo.

### ¿Cómo optimizaría costos de operación?

La contención de costos operativos se basaría en la arquitectura de costo cero como línea base, priorizando el modelo gratuito por defecto y evaluando su costo real (en términos de latencia y tasa de error) antes de considerar cualquier transición hacia un modelo comercial pequeño. La principal palanca de ahorro radicaría en minimizar las invocaciones al proveedor externo mediante el uso intensivo de caché y el filtrado previo por relevancia léxica. Cuando el proveedor no responda, la degradación determinista local atiende la consulta sin costo alguno de tokens, manteniendo una política estricta sin failover automático a opciones de pago. Operacionalmente, la infraestructura mantendría una huella extremadamente ligera basada en SQLite en un archivo local sin servidores de base de datos dedicados ni clusters, ejecutando un único proceso de API y un frontend estático. Finalmente, se realizaría un saneamiento continuo del corpus documental previo al pase a producción, eliminando textos redundantes que ensucien la recuperación o provoquen contextos innecesariamente voluminosos.

---

## F. Persistencia y gestión de datos

### ¿Qué mecanismo de almacenamiento seleccioné?

**SQLite** mediante la biblioteca estándar de Python (`sqlite3`), en un archivo local
(`storage/walle.db`), con WAL, `busy_timeout`, consultas parametrizadas y esquema versionado con
`PRAGMA user_version`.

### ¿Por qué lo seleccioné?

Se eligió SQLite debido a su nula sobrecarga operativa y su perfecta adecuación al modelo de despliegue local y monousuario, eliminando la necesidad de instalar, configurar, respaldar y monitorizar un servidor de base de datos independiente. Frente a una carga proyectada de 100.000 consultas diarias (~3 millones de registros mensuales o 36 millones al año), SQLite responde con holgura en un equipo modesto garantizando durabilidad y aislamiento transaccional gracias a la configuración de Write-Ahead Logging (WAL) y una política de sincronización adecuada. La concurrencia de escritura multihilo en la API se solventa limpiamente mediante conexiones aisladas por hilo y el ajuste de `busy_timeout`, evitando bloqueos de contención (verificado empíricamente con pruebas de concurrencia de diez hilos simultáneos). Además, el acceso a los datos se encuentra estrictamente desacoplado tras el protocolo `RepositorioConsultas`, permitiendo una eventual migración de motor sin necesidad de reescribir la lógica de la aplicación.

### ¿Qué ventajas tiene para este escenario?

Para este escenario específico, SQLite aporta una simplicidad operativa insuperable al residir toda la persistencia en un único archivo local, facilitando copias de respaldo y portabilidad inmediata entre sistemas Linux, macOS y Windows sin requerir administración de infraestructura. A su vez, garantiza privacidad por diseño al mantener los datos de las consultas de los asesores fuera del control de versiones (`.gitignore`), todo ello con costo cero de infraestructura y aprovechando las librerías nativas del lenguaje sin dependencias externas adicionales.

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
