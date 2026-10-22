# Plan 002 — Persistencia de consultas

**Característica:** Almacenamiento local de las consultas realizadas al asistente Walle
**Versión:** 1.0 · Estado: para revisión
**Especificación:** `especificaciones/002-persistencia/especificacion.md`
**Tareas:** `especificaciones/002-persistencia/tareas.md`

---

## 1. Arquitectura propuesta

```
    ┌──────────────────────────────────────────────────────┐
    │   API FastAPI (capa api)                            │
    │   POST  /api/consultar        → registra la consulta │
    │   GET   /api/historial        → lista todas          │
    │   GET   /api/historial/{id}   → consulta por índice  │
    │   DELETE /api/historial/{id}  → borra por índice     │
    └───────────────┬──────────────────────────────────────┘
                    │ depende del protocolo, no de SQLite
    ┌───────────────▼──────────────────────────────────────┐
    │  Protocolo RepositorioConsultas (dominio/persistencia)│
    │  registrar() · listar() · obtener(id) · eliminar(id)  │
    └──┬───────────────────────────────┬───────────────────┘
       │                               │
┌──────▼─────────────┐   ┌─────────────▼───────────────────┐
│ RepositorioSQLite  │   │ RepositorioEnMemoria           │
│ storage/walle.db   │   │ (doble para pruebas)            │
│ WAL · versionado   │   │                                 │
└────────────────────┘   └─────────────────────────────────┘
```

### 1.1 Principio de acoplamiento

La API y el orquestador **(characteristic 001)** dependen del **protocolo** `RepositorioConsultas`, nunca de SQLite. Esto permite:

- probar el dominio sin tocar el disco (doble en memoria);
- persistir en un repositorio en memoria si la base no está disponible, sin cambiar el flujo de la API;
- evolver el motor de base de datos en el futuro (pregunta del cuestionario) sin reescribir la aplicación.

### 1.2 Esquema de la base

Archivo: `storage/walle.db` (ruta configurable con `WALLE_DB_PATH`).

```sql
CREATE TABLE IF NOT EXISTS consultas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta     TEXT    NOT NULL,
    fecha_hora   TEXT    NOT NULL,   -- ISO-8601 UTC, p. ej. 2026-10-21T15:04:05.123456+00:00
    respuesta    TEXT    NOT NULL,
    fuentes      TEXT    NOT NULL,   -- JSON: [{"documento": "...", "fragmento": "..."}]
    estado       TEXT    NOT NULL,   -- Exitosa | Sin información suficiente | Bloqueada por seguridad
    duracion_ms  INTEGER NOT NULL,
    modelo       TEXT    NOT NULL DEFAULT ''   -- '' cuando no se invocó al proveedor
);

CREATE INDEX IF NOT EXISTS ix_consultas_fecha_hora ON consultas (fecha_hora DESC);
```

**Decisiones de esquema**

| Columna | Tipo | Motivo |
|---------|------|--------|
| `id` | INTEGER PK AUTOINCREMENT | Índice estable y monotónico, que es la clave que usa el historial (`/api/historial/{id}`) |
| `pregunta` | TEXT NOT NULL | Requisito del enunciado |
| `fecha_hora` | TEXT NOT NULL | ISO-8601 UTC: orden lexicográfico correcto, legible y portable entre motores |
| `respuesta` | TEXT NOT NULL | Requisito del enunciado; se guarda también en estado bloqueado, siempre el mensaje genérico |
| `fuentes` | TEXT NOT NULL (JSON) | Requisito del enunciado; JSON permite reconstruir la estructura documento/fragmento sin tabla aparte |
| `estado` | TEXT NOT NULL | Requisito del enunciado; se valida contra el enum `Estado` al escribir |
| `duracion_ms` | INTEGER NOT NULL | Observabilidad (constitución §7) |
| `modelo` | TEXT NOT NULL DEFAULT '' | Trazabilidad del proveedor usado; vacío en consultas que no invocaron al modelo |

**Sin `correlation_id`**: decisión del responsable del proyecto; la trazabilidad fina se resuelve con las trazas de aplicación y no en la base.

**Versionado del esquema**: `PRAGMA user_version` = 1. La inicialización es idempotente (`CREATE TABLE IF NOT EXISTS`) y solo altera el esquema si la versión guardada es menor que la esperada.

### 1.3 Modo WAL y ajustes de conexión

```python
conexion.execute("PRAGMA journal_mode = WAL")
conexion.execute("PRAGMA foreign_keys = ON")
conexion.execute("PRAGMA synchronous = NORMAL")   # equilibrio durability/rendimiento en WAL
conexion.execute("PRAGMA busy_timeout = 5000")     # espera acotada ante bloqueo (RNF-04)
```

### 1.4 Concurrencia

- **Conexión por hilo**: cada hilo obtiene su propia conexión mediante `threading.local`; se evita compartir objetos `sqlite3.Connection` entre hilos.
- **`check_same_thread=False`** no es necesario al aislar por hilo, pero se documenta la decisión.
- **Escrituras serializadas**: la escritura de una consulta es una transacción corta (`with conexion:`) sobre una única fila; el riesgo de contención es bajo.
- **`busy_timeout`**: si otra escritura mantiene el bloqueo, la conexión espera hasta 5 s antes de fallar.
- El servidor ASGI de FastAPI ejecuta las rutas en un threadpool, por lo que el aislamiento por hilo es el mecanismo adecuado.

### 1.5 Modo degradado

Si la base no puede abrirse o inicializarse (ruta inválida, permisos, disco lleno):

1. la aplicación **no se cae**: se construye un `RepositorioEnMemoria` como respaldo;
2. se registra la causa en las trazas (sin volcar rutas del sistema al cliente);
3. `GET /api/salud` reporta `persistencia.disponible = false` y el motivo codificado;
4. las consultas siguen respondiendo con normalidad; simplemente no quedan registradas.

### 1.6 API de historial

| Método | Ruta | Respuesta | Códigos |
|--------|------|-----------|---------|
| `GET` | `/api/historial` | Lista de consultas, de la más reciente a la más antigua | 200 (arreglo vacío si no hay) |
| `GET` | `/api/historial/{id}` | Consulta completa con `fuentes` estructuradas | 200, 404 |
| `DELETE` | `/api/historial/{id}` | Resultado de la eliminación | 200, 404 |

- El listado devuelve todos los registros sin paginación (RNF-01: < 100 ms para 1000 filas). Si en el futuro el volumen lo exige, se añade `?limite=` y `?desde=` sin romper el contrato actual.
- Los elementos del listado incluyen `id`, `pregunta`, `fecha_hora`, `estado`, `duracion_ms`, `respuesta` y `fuentes`, para que el panel lateral pueda pintar la conversación con una sola llamada.
- El borrado responde `404` si el índice no existe y **no** altera el resto del historial.
- No hay endpoint de borrado masivo (fuera de alcance).

### 1.7 Módulos

```
src/walle/persistencia/
├── __init__.py
├── esquema.py         # DDL, versión del esquema, funciones de inicialización
├── modelo.py          # dataclass Consulta (dominio de persistencia)
└── repositorio.py     # protocolo RepositorioConsultas, RepositorioSQLite, RepositorioEnMemoria
```

`src/walle/api/rutas.py` incorpora el router de historial (`historial.py` si crece).

## 2. Componentes

| Componente | Responsabilidad | Requisitos |
|------------|-----------------|------------|
| `esquema.py` | Crear el esquema de forma idempotente, versionar con `PRAGMA user_version` | RNF-02, RNF-03 |
| `modelo.py` | `Consulta` con serialización a/from JSON de `fuentes` | RF-01, RF-05 |
| `repositorio.py` (protocolo) | Contrato de persistencia que consume la aplicación | RF-01…RF-05 |
| `repositorio.py` (SQLite) | Implementación con conexiones por hilo, WAL y transacciones | RF-01, RNF-01…RNF-05 |
| `repositorio.py` (memoria) | Doble para pruebas y modo degradado | RF-05, RNF-05 |
| `api/historial.py` | Endpoints de listado, consulta por índice y borrado | RF-02, RF-03, RF-04 |
| `api/salud` (001) | Reporta disponibilidad de la persistencia | RF-05, RNF-05 |

## 3. Estrategia de pruebas

| Nivel | Contenido | Notas |
|-------|-----------|-------|
| `tests/unit/test_repositorio.py` | Alta, lectura por índice, listado ordenado, borrado, índices inexistentes, estado bloqueado sin contenido sensible, reinicio sobre la misma base, ruta configurable | SQLite en archivo temporal (`tmp_path`) y en memoria (`:memory:`) |
| `tests/unit/test_rendimiento_persistencia.py` | 1000 inserciones y lectura del historial por debajo de los umbrales de RNF-01 | Test informativo: registra la duración y falla solo si excede un margen amplio, para no ser flaky en CI lento |
| `tests/integration/test_api_historial.py` | Los tres endpoints con `TestClient`: 200, 404 y efecto real del borrado | Repositorio SQLite en archivo temporal inyectado por configuración |
| `tests/integration/test_concurrencia.py` | Diez consultas simultáneas → diez filas, sin "database is locked" | Threads con `ThreadPoolExecutor` |
| `tests/integration/test_api_salud.py` | `persistencia.disponible` en `true` y en `false` (ruta inválida) | Modo degradado |

**Reglas de la suite**

- Ninguna prueba usa la base real del repositorio: todas apuntan a rutas temporales.
- El doble en memoria y el SQLite deben compartir contrato: se ejecuta la **misma batería de aserciones** contra ambas implementaciones (prueba parametrizada), de modo que el doble nunca se desvía del comportamiento real.
- No se requiere red ni modelo para ninguna prueba de esta característica.
