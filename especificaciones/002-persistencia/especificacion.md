# Especificación 002 — Persistencia de consultas

**Característica:** Almacenamiento local de las consultas realizadas al asistente Walle
**Versión:** 1.0 · Estado: para revisión
**Documentos relacionados:** `constitucion/constitucion.md`, `especificaciones/001-api/especificacion.md`, `especificaciones/002-persistencia/plan.md`, `especificaciones/002-persistencia/tareas.md`

---

## 1. Contexto

Cada consulta al asistente produce información con valor operativo y de auditoría: qué preguntó el asesor, qué se respondió, con qué fuentes y con qué resultado. El enunciado de la prueba exige que el sistema almacene **pregunta, fecha y hora, respuesta, fuentes utilizadas y estado de la respuesta**, con tres estados posibles: `Exitosa`, `Sin información suficiente` y `Bloqueada por seguridad`.

Ese registro cumple dos funciones distintas que no deben confundirse: (a) alimentar el panel lateral del frontend con las consultas anteriores, y (b) dejar evidencia para el análisis de calidad y de seguridad del asistente.

El almacenamiento es local y sin servidor: SQLite en un archivo dentro de `storage/`, ruta ya contemplada en `.gitignore` para que ni la base ni su contenido lleguen al repositorio.

## 2. Objetivo

Persistir de forma confiable y trazable cada consulta procesada por el asistente, y exponer mediante la API un historial navegable que permita listar todas las consultas, consultar una en particular por su índice y eliminar una por su índice.

## 3. Alcance

### 3.1 Dentro del alcance

- Esquema de la base y su inicialización automática (idempotente y versionada).
- Registro de cada consulta: pregunta, fecha y hora, respuesta, fuentes, estado, duración y modelo utilizado.
- API de historial: listado de todas las consultas, consulta de una consulta por índice y borrado por índice.
- Confidentialidad de lo persistido: nunca se almacenan datos sensibles ni contenido restringido.
- Modo degradado: si la base no está disponible, el sistema sigue operando y lo reporta en el punto de salud.
- Pruebas automatizadas del repositorio y de los endpoints de historial.

### 3.2 Fuera del alcance

- Persistencia de usuarios, sesiones o autenticación.
- Análisis semántico o indexación vectorial del historial: no hay RAG sobre consultas.
- Replicación, réplicas de lectura o alta disponibilidad: es un despliegue local.
- Migración de datos entre versiones de esquema más allá del versionado inicial con `PRAGMA user_version`.
- Exportación, respaldos programados o retención automática: se documentan como mejoras futuras.
- Endpoint de borrado masivo del historial (no solicitado).

## 4. Requerimientos funcionales

### RF-01 — Registro de cada consulta
Al responder una consulta, el sistema registra en la base una fila con: `id` (índice entero autoincremental), `pregunta` (texto recibido), `fecha_hora` (momento de la consulta en ISO-8601 UTC), `respuesta` (texto devuelto al usuario), `fuentes` (lista de documentos y fragmentos citados, serializada como JSON), `estado` (uno de los tres estados válidos), `duracion_ms` (tiempo total de la consulta) y `modelo` (modelo usado, o vacío si no se invocó al proveedor). El registro ocurre también cuando el estado es `Sin información suficiente` o `Bloqueada por seguridad`. La escritura es una transacción única: o se guarda la fila completa, o no se guarda nada.

### RF-02 — Listado del historial
`GET /api/historial` devuelve **todas** las consultas registradas, ordenadas de la más reciente a la más antigua, en un arreglo JSON. Cada elemento expone el índice, la pregunta, la fecha y hora, el estado y la duración; el contenido completo de la respuesta y las fuentes se incluyen en el listado para que el panel lateral pueda mostrar la conversación sin una segunda llamada. Si no hay consultas, devuelve un arreglo vacío y código 200.

### RF-03 — Consulta por índice
`GET /api/historial/{id}` devuelve la consulta indicada con todos sus campos, incluidas las fuentes estructuradas (documento y fragmento). Si el índice no existe, devuelve `404` con un mensaje que indica que la consulta no fue encontrada, sin filtrar información interna.

### RF-04 — Borrado por índice
`DELETE /api/historial/{id}` elimina la consulta indicada y devuelve el resultado de la operación. Si el índice no existe, devuelve `404` con el mismo mensaje del caso anterior. La operación no afecta a las demás consultas.

### RF-05 — Confidencialidad de lo persistido
La base no contiene nunca información clasificada: en una consulta con estado `Bloqueada por seguridad` se persiste el **mensaje genérico** de rechazo, nunca el contenido que intentó extraerse ni el fragmento restringido que la originó; en una consulta `Exitosa` se persiste únicamente lo ya validado por los guardrails de salida. Las fuentes persistidas provienen siempre de la allowlist de documentos permitidos.

## 5. Requerimientos no funcionales

### RNF-01 — Rendimiento
La escritura de una consulta no añade más de 10 ms al tiempo de respuesta de la API en condiciones normales, y la lectura del historial completo responde en menos de 100 ms para un volumen de 1000 consultas. El listado utiliza un índice sobre la fecha de registro.

### RNF-02 — Durabilidad e integridad
La base opera en modo WAL, con integridad referencial y de escritura activadas. Una consulta confirmada por la API está confirmada en disco: si el proceso muere después de responder, la fila permanece. El esquema se crea de forma idempotente y versionada mediante `PRAGMA user_version`, de modo que abrir la aplicación repetidamente no altera los datos existentes.

### RNF-03 — Portabilidad
La persistencia usa únicamente la biblioteca estándar (`sqlite3`), sin servidor de base de datos ni dependencias externas. El archivo de base de datos vive en `storage/` (ignorado por git) y su ruta es configurable. El esquema y el código funcionan igual en Linux, macOS y Windows, con rutas resueltas de forma portable.

### RNF-04 — Concurrencia
El sistema atiende varias consultas simultáneas sin producir errores de base bloqueada: las escrituras se serializan, el tiempo de espera de bloqueo es acotado y las conexiones se aíslan por hilo. La API mantiene su disponibilidad cuando varias peticiones llegan a la vez.

### RNF-05 — Trazabilidad y calidad de implementación
Todas las sentencias SQL se ejecutan con parámetros vinculados (nunca concatenación de cadenas), lo que elimina la inyección SQL por construcción. La operación de escritura mide y registra su duración, y la escritura de una consulta es idempotente respecto del estado de la base: un fallo de persistencia no invalida la respuesta ya entregada al usuario, pero queda registrado y visible en el punto de salud.

## 6. Riesgos

| # | Riesgo | Impacto | Mitigación prevista |
|---|--------|---------|---------------------|
| R-01 | **Pérdida o corrupción de datos** por cierre abrupto del proceso o del equipo | Se pierde el historial y con él la trazabilidad de las consultas | Modo WAL, transacciones por escritura, nivel `synchronous` duradero, verificación de integridad documentada y procedimiento de copia de seguridad del archivo |
| R-02 | **Inyección SQL** por construir consultas con concatenación | Acceso no autorizado o corrupción de la base | Uso exclusivo de parámetros vinculados y de `sqlite3` con consultas parametrizadas; regla de lint y revisión de código |
| R-03 | **Fuga de información sensible a la base de datos** (token interno, credenciales, contenido restringido) | Incumplimiento de confidencialidad, y ahora también en disco | Solo se persiste la respuesta ya validada por los guardrails; el mensaje de bloqueo es genérico; los documentos restringidos nunca llegan a las fuentes (RF-05) |
| R-04 | **"Database is locked"** por escrituras concurrentes desde la API | Errores intermitentes en la consulta del asesor | Conexiones aisladas por hilo, `busy_timeout`, WAL, escrituras serializadas en una transacción corta y prueba de concurrencia |
| R-05 | **Volcado accidental de la base al repositorio** (`.db` es un binario con datos de los usuarios) | Fuga de información y ruido en el repositorio | `storage/*.db` en `.gitignore`, verificación en el checklist de entrega y ruta configurable fuera del árbol versionado por defecto |

## 7. Criterios de aceptación (Gherkin)

```gherkin
Característica: Persistencia e historial de consultas del asistente Walle

  Escenario: Registro de una consulta exitosa (RF-01)
    Dado un repositorio de consultas vacío
    Cuando se procesa la consulta "¿Cuál es el monto máximo del Crédito Productivo Impulso?" con estado "Exitosa"
    Entonces existe exactamente una fila en el historial
    Y la fila contiene la pregunta, la respuesta, el estado "Exitosa", una fecha y hora ISO-8601 en UTC y una duración mayor o igual a cero
    Y sus fuentes corresponden a documentos permitidos

  Escenario: Registro de una consulta sin información suficiente (RF-01)
    Dado un repositorio de consultas vacío
    Cuando se procesa una consulta fuera del corpus con estado "Sin información suficiente"
    Entonces el historial contiene una fila
    Y la fila guarda el mensaje canónico "No tengo información suficiente para responder."
    Y la fila tiene la lista de fuentes vacía

  Escenario: Registro de una consulta bloqueada por seguridad (RF-01, RF-05)
    Dado un repositorio de consultas vacío
    Cuando se procesa un intento de obtener el token interno con estado "Bloqueada por seguridad"
    Entonces el historial contiene una fila
    Y la fila guarda el mensaje genérico de rechazo
    Y la fila no contiene el token interno ni el contenido restringido
    Y la fila tiene la lista de fuentes vacía

  Escenario: Listado de todas las consultas (RF-02)
    Dado tres consultas registradas en momentos distintos
    When el cliente solicita GET /api/historial
    Entonces la respuesta HTTP es 200
    Y el cuerpo es un arreglo de tres elementos
    Y el orden es de la más reciente a la más antigua
    Y cada elemento incluye índice, pregunta, fecha y hora, estado y duración

  Escenario: Historial vacío (RF-02)
    Dado un repositorio sin consultas
    When el cliente solicita GET /api/historial
    Entonces la respuesta HTTP es 200
    Y el cuerpo es un arreglo vacío

  Escenario: Consulta por índice (RF-03)
    Dado una consulta registrada con índice 1
    When el cliente solicita GET /api/historial/1
    Entonces la respuesta HTTP es 200
    Y el cuerpo incluye la pregunta, la respuesta, el estado y las fuentes estructuradas con documento y fragmento

  Escenario: Consulta por índice inexistente (RF-03)
    Dado un repositorio con consultas
    When el cliente solicita GET /api/historial/9999
    Entonces la respuesta HTTP es 404
    Y el mensaje indica que la consulta no fue encontrada
    Y el mensaje no expone detalles internos

  Escenario: Borrado por índice (RF-04)
    Dado tres consultas registradas
    When el cliente solicita DELETE /api/historial/2
    Entonces la consulta con índice 2 deja de existir
    Y las consultas 1 y 3 siguen existiendo
    Y GET /api/historial devuelve dos elementos

  Escenario: Borrado de un índice inexistente (RF-04)
    Dado un repositorio con consultas
    When el cliente solicita DELETE /api/historial/9999
    Entonces la respuesta HTTP es 404
    Y el historial no se modifica

  Escenario: Aislamiento entre pruebas y reinicio de la aplicación (RNF-02, RNF-03)
    Dado una base de datos creada en una ruta temporal
    When la aplicación se abre por segunda vez sobre esa misma base
    Entonces el esquema no se altera y las consultas siguen disponibles
    Y el archivo de base de datos queda fuera del árbol versionado

  Escenario: Base de datos no disponible (RF-05, RNF-05)
    Dado que la ruta de la base de datos no puede abrirse
    When el cliente realiza una consulta
    Entonces la API responde 200 con una respuesta válida
    Y el punto de salud reporta que la persistencia no está disponible
    Y el fallo queda registrado en las trazas

  Escenario: Escrituras concurrentes (RNF-04)
    Dado diez consultas procesadas de forma simultánea
    When todas las consultas terminan
    Entonces el historial contiene exactamente diez filas
    Y ninguna petición falló por bloqueo de la base de datos
```

## 8. Trazabilidad

| Requisito | Escenario Gherkin | Prueba prevista |
|-----------|------------------|-----------------|
| RF-01 | Registro exitoso, sin información suficiente, bloqueada | `tests/unit/test_repositorio.py` |
| RF-02 | Listado de todas las consultas, historial vacío | `tests/integration/test_api_historial.py` |
| RF-03 | Consulta por índice, índice inexistente | `tests/integration/test_api_historial.py` |
| RF-04 | Borrado por índice, índice inexistente | `tests/integration/test_api_historial.py` |
| RF-05 | Registro bloqueada, base no disponible | `tests/unit/test_repositorio.py`, `tests/integration/test_api_salud.py` |
| RNF-01 | Rendimiento de escritura y lectura | `tests/unit/test_rendimiento_persistencia.py` (no bloqueante) |
| RNF-02 | Reinicio de la aplicación | `tests/unit/test_repositorio.py` |
| RNF-03 | Ruta configurable y portable | `tests/unit/test_repositorio.py` |
| RNF-04 | Escrituras concurrentes | `tests/integration/test_concurrencia.py` |
| RNF-05 | Parámetros vinculados y fallo de persistencia | `tests/unit/test_repositorio.py` |
