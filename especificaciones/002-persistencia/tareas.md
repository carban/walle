# Tareas 002 — Persistencia de consultas

**Característica:** Almacenamiento local de las consultas realizadas al asistente Walle
**Versión:** 1.0 · Estado: para revisión
**Especificación:** `especificaciones/002-persistencia/especificacion.md` · **Plan:** `especificaciones/002-persistencia/plan.md`

**Convenciones**
- Tareas numeradas desde `T-101` para no solaparse con la característica 001.
- TDD estricto (constitución §3): primero la prueba, después el código.
- Depende de `001-api` en curso: el protocolo `RepositorioConsultas` nació en `T-024`; aquí se completa su implementación real.

---

## Fase 1 — Modelo y esquema

- [x] **T-101** Definir `src/walle/persistencia/modelo.py`: dataclass `Consulta` con `id`, `pregunta`, `fecha_hora`, `respuesta`, `fuentes` (lista de `Fuente`), `estado`, `duracion_ms`, `modelo`, y métodos de serialización a/desde fila de SQLite y a/desde JSON de API.
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_consulta_guarda_todos_los_campos` — ida y vuelta sin pérdida; `fuentes` se guarda como JSON válido.
- [x] **T-102** Implementar `src/walle/persistencia/esquema.py`: DDL de la tabla `consultas`, índice por fecha, `PRAGMA user_version` y creación idempotente.
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_el_esquema_es_idempotente`, `test_la_version_del_esquema_queda_registrada` — abrir dos veces la misma base no altera los datos ni falla; `user_version` queda en 1.
- [x] **T-103** Implementar la apertura de conexión con los PRAGMA de la base (WAL, `foreign_keys`, `synchronous`, `busy_timeout`) y el aislamiento por hilo (`threading.local`).
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_escrituras_concurrentes_no_producen_bloqueos` — valida de forma indirecta WAL y `busy_timeout`; no hay una prueba específica de PRAGMA.

## Fase 2 — Repositorio

- [x] **T-104** Implementar `RepositorioSQLite.registrar(consulta) -> int`: inserción parametrizada en transacción única, devuelve el `id` generado; `fecha_hora` por defecto en ISO-8601 UTC.
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_registrar_devuelve_indice`, `test_consulta_guarda_todos_los_campos` — la fila existe con todos los campos.
- [x] **T-105** Implementar `listar() -> list[Consulta]` ordenado de más reciente a más antigua.
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_listar_ordenado_de_mas_reciente_a_mas_antigua`, `tests/unit/test_repositorio.py::test_repositorio_lista_de_mas_reciente_a_mas_antigua` con tres inserciones en instantes distintos.
- [x] **T-106** Implementar `obtener(id) -> Consulta | None` y `eliminar(id) -> bool`.
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_obtener_indice_inexistente_devuelve_none`, `test_eliminar_por_indice`; equivalentes en `tests/unit/test_repositorio.py`.
- [x] **T-107** Implementar `RepositorioEnMemoria` con la misma semántica, usadas en las pruebas y como modo degradado.
  - Criterio: `tests/unit/test_repositorio.py`, `tests/unit/test_repositorio_sqlite.py` — la misma semántica se verifica en ambas implementaciones.
- [x] **T-108** Registrar siempre la consulta desde el orquestador (éxito, insuficiencia y bloqueo), con el mensaje genérico en el estado bloqueado.
  - Criterio: `tests/integration/test_api_historial.py::test_consulta_registrada_aparece_en_el_historial`, `test_la_consulta_bloqueada_tambien_queda_registrada` — una fila por consulta; el caso bloqueado no contiene el token.
- [x] **T-109** Implementar el modo degradado: si la base no abre, usar el repositorio en memoria y registrar la causa en las trazas.
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_el_modo_degradado_usa_memoria`, `tests/integration/test_api_historial.py::test_salud_informa_la_persistencia`.

## Fase 3 — API de historial

- [x] **T-110** Crear `src/walle/api/historial.py` con el router: `GET /api/historial`, `GET /api/historial/{id}`, `DELETE /api/historial/{id}`.
  - Criterio: `tests/integration/test_api_historial.py` — 200 con lista (o lista vacía), 200 con el detalle, 200/404 en el borrado.
- [x] **T-111** Definir los esquemas de respuesta del historial en `src/walle/api/esquema.py` (`ResumenConsulta`, `DetalleConsulta`) y el manejo de `404` con mensaje "la consulta no fue encontrada", sin detalles internos.
  - Criterio: `tests/integration/test_api_historial.py::test_consulta_por_indice_inexistente`, `tests/integration/test_api_consulta.py::test_error_no_controlado_no_filtra_detalles`.
- [x] **T-112** Registrar el router en `src/walle/main.py` y ampliar `GET /api/salud` con el bloque `persistencia` (`disponible`, `motor`, `ruta` no sensible).
  - Criterio: `tests/integration/test_api_historial.py::test_salud_informa_la_persistencia`, `tests/unit/test_repositorio_sqlite.py::test_el_modo_degradado_usa_memoria` — `disponible: true` con base operativa y `false` con ruta inválida.

## Fase 4 — Calidad y seguridad de la persistencia

- [x] **T-113** Verificar que todas las sentencias SQL usan parámetros vinculados (revisión assisted + test que intenta una pregunta con `'; DROP TABLE consultas; --` y comprueba que la tabla sigue existiendo).
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_una_pregunta_con_sql_no_se_interpreta`.
- [x] **T-114** Prueba de concurrencia: diez escrituras simultáneas terminan con exactamente diez filas y ningún error de bloqueo.
  - Criterio: `tests/unit/test_repositorio_sqlite.py::test_escrituras_concurrentes_no_producen_bloqueos`.
- [x] **T-115** Prueba de rendimiento no bloqueante: inserción de 1000 filas y lectura del historial dentro de los umbrales de RNF-01.
  - Criterio: `tests/unit/test_rendimiento_persistencia.py` — registra la duración; falla solo con margen amplio.
- [x] **T-116** Verificar que `storage/` y `storage/*.db` siguen ignorados por git y que la ruta por defecto está fuera del árbol versionado.
  - Criterio: revisión manual de `.gitignore` y de `Settings().walle_db_path`; no hay una prueba automatizada específica de la ruta por defecto.

## Fase 5 — Documentación de la característica

- [x] **T-117** Actualizar `README.md` con la sección de persistencia: dónde vive la base, cómo se inspecciona, cómo se respalda y cómo se borra.
- [x] **T-118** Registrar en `docs/Cuestionario.md` las respuestas de persistencia (mecanismo, elección, motor futuro y razonamiento).
- [x] **T-119** Revisar la matriz de trazabilidad §8 de la especificación: cada RF/RNF con al menos una prueba.
- [x] **T-120** Actualizar `constitucion/constitucion.md` con la decisión registrada del esquema (D-07) si el responsable lo aprueba.

---

## Dependencias entre tareas

```
T-101 → T-102 → T-103 → T-104 → T-105 → T-106 → T-107 → T-108 → T-109
                                   ↓
                    T-110 → T-111 → T-112
                                   ↓
                    T-113 → T-114 → T-115 → T-116 → T-117 → T-118 → T-119 → T-120
```

## Criterio de cierre de la característica 002

- `uv run pytest` en verde, sin red y sin tocar la base real.
- Las 5 RF y los 5 RNF cubiertos por pruebas (matriz §8 verificada).
- La base se crea sola en el primer arranque, es idempotente y sobrevive a un reinicio.
- `GET /api/historial`, `GET /api/historial/{id}` y `DELETE /api/historial/{id}` operativos y probados.
- El punto de salud informa la disponibilidad de la persistencia.
- Cero secretos y cero datos restringidos en la base (verificado por prueba).
