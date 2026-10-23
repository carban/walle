# Constitución del Proyecto Walle

**Asistente interno para asesores comerciales**
Versión 1.0 · Estado: ratificada · Alcance: todo el código y la documentación del repositorio.

---

## Propósito

Walle responde consultas de asesores comerciales sobre créditos, microseguros, inversiones, criptomoneda, procedimientos y políticas internas, fundamentando **toda** respuesta en la documentación oficial de `Data/` y citando sus fuentes. La prioridad no es la sofisticación del modelo, sino la confianza: una respuesta sin evidencia documental no se emite.

## 1. Seguridad por defecto

- **Mínimo privilegio documental**: solo se consultan los documentos permitidos. Los archivos clasificados como restringidos se excluyen del índice de contexto y nunca se citan, imprimen ni registran.
- **Validación en dos frentes**: la entrada se sanea antes de tocar el modelo; la salida se inspecciona contra los patrones de dato sensible antes de devolverse o persistirse.
- **Bloqueo explícito**: cualquier intento de escalar privilegios o extraer material restringido termina en estado `Bloqueada por seguridad`, con registro del evento y sin contenido sensible.
- **Credenciales fuera del código**: la clave del proveedor vive en `.env`, nunca se versiona, nunca aparece en logs ni en trazas de error.
- **Mínimo registro**: se persiste lo necesario para atender la consulta y auditar el uso, nunca el secreto.

## 2. Calidad

- La calidad se define antes de codificar: cada requisito funcional y no funcional crítico tiene un criterio de aceptación verificable (Gherkin).
- Cada cambio llega con una prueba que lo demuestra; una prueba que falla bloquea la entrega.
- La suite es hermética: no depende de red, de reloj real ni de orden de ejecución; el tiempo y el proveedor se inyectan.
- La cobertura se mide de forma continua y las regresiones se tratan con la misma urgencia que los defectos nuevos.
- El código se revisa contra esta constitución antes de integrarse.

## 3. TDD

- Ciclo rojo → verde → refactor, aplicado de forma estricta: primero la prueba que falla, después el mínimo código que la satisface.
- Las pruebas de integración contra el proveedor real se marcan y se ejecutan de forma opt-in, separadas de la suite hermética.
- Los casos límite son parte del diseño: entrada vacía, base documental vacía, duplicados, caracteres especiales y consultas extensas se prueban explícitamente.
- La refactorización no cambia el comportamiento observable: si el comportamiento cambia, cambia la prueba primero.

## 4. Uso responsable de IA

- **La IA redacta; el sistema decide.** Los documentos permitidos, los estados válidos, el formato de salida y los criterios de suficiencia están fijados en código y son auditables.
- El proveedor de modelos es intercambiable y su configuración es externa; ninguna decisión de negocio vive dentro de un prompt.
- Se prioriza el modelo gratuito disponible; el uso de modelos de pago requiere ratificación expresa.
- Cuando el modelo falla o no hay red, el sistema degrada a una respuesta determinista construida con la documentación local, en lugar de inventar contenido.
- Ningún dato sensible se envía a un tercero, y el prompt de sistema lo declara de forma explícita.

## 5. Mantenibilidad

- Estructura explícita por capas (`api`, `recuperacion`, `modelo`, `seguridad`, `persistencia`), sin estado global oculto ni acoplamiento entre capas.
- Contratos tipados en los bordes de la aplicación; cualquier cambio de contrato se refleja en esquema, prueba y documentación.
- Configuración por entorno con valores por defecto seguros: el sistema arranca sin secretos y falla de forma clara si le faltan.
- La documentación técnica es parte del entregable y se actualiza en el mismo cambio que el código.
- Entorno declarativo y reproducible (`uv`, `npm`), con dependencias justificadas.

## 6. Optimización de costos

- El costo por consulta se mantiene en cero o mínimo mediante: modelo gratuito por defecto, filtrado previo a la invocación y reutilización del corpus indexado en memoria.
- No se invoca al modelo cuando la consulta no es respondible con la documentación disponible.
- El contexto enviado se acota a lo que la pregunta exige; el corpus se filtra por relevancia antes de enviarse.
- Se registra el consumo por consulta para poder optimizar con evidencia y no con intuición.

## 7. Observabilidad

- Cada consulta deja rastro persistido: pregunta, fecha y hora, respuesta, fuentes utilizadas, estado y duración.
- Los errores se distinguen del resultado de negocio: un fallo del proveedor no se confunde con "sin información suficiente".
- El sistema expone un punto de salud que permite verificar dependencias (proveedor, base de datos, corpus).
- Las trazas evitan datos sensibles y son suficientes para reconstruir qué documento se usó y con qué resultado.
- Los umbrales de estado permiten distinguir la operación normal de la degradación del proveedor.

## Cumplimiento

Cualquier desviación de esta constitución se documenta como decisión explícita, con su justificación y fecha de revisión.

---

### Decisiones registradas

| # | Decisión | Estado | Fecha |
|---|----------|--------|-------|
| D-01 | Modelo principal `cohere/north-mini-code:free` (gratuito) | Aceptada | 2026-10-21 |
| D-02 | Sin streaming: respuesta JSON única con indicador de carga en el cliente | Aceptada | 2026-10-21 |
| D-03 | Degradación a respuesta extractiva determinista si el proveedor falla (nunca a modelo de pago) | Aceptada | 2026-10-21 |
| D-04 | Estructura con `src/` en la raíz del repositorio | Aceptada | 2026-10-21 |
| D-05 | Persistencia local SQLite en `storage/` | Aceptada | 2026-10-21 |
| D-06 | Frontend React + npm, estilo ChatGPT con panel lateral de historial | Aceptada | 2026-10-21 |
| D-07 | Esquema de la tabla `consultas`: `id`, `pregunta`, `fecha_hora`, `respuesta`, `fuentes` (JSON), `estado`, `duracion_ms`, `modelo` (sin `correlation_id`) | Aceptada | 2026-10-21 |
| D-08 | Historial consultable por listado y por índice, con borrado por índice (sin borrado masivo) | Aceptada | 2026-10-21 |
| D-09 | Se registra también la consulta bloqueada por seguridad, guardando el mensaje genérico | Aceptada | 2026-10-21 |
| D-10 | Recuperación documental con Okapi BM25 (índice por documento y por sección), complementada con sinónimos del dominio, entidades y moneda | Aceptada | 2026-10-22 |
