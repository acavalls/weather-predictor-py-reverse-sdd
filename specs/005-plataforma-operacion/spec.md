# Feature Specification: SPEC-05 — Plataforma y operación (transversal)

**Feature Branch**: `specs/005-plataforma-operacion` (sin rama git: hook `before_specify` saltado por decisión del usuario)

**Created**: 2026-11-14

**Status**: Draft

**Input**: Especificación inversa de `propuesta-particion-specs.md` (PARTE 2, SPEC-05). Spec de ingeniería inversa: documenta el comportamiento EXISTENTE de la plataforma: configuración y constantes, contratos de error HTTP comunes, persistencia, credenciales, dependencias, runtime, logs e higiene del repositorio. No es una feature nueva: es la especificación formal de lo que el sistema YA hace, para que sirva de contrato en la modernización.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Contrato de errores HTTP con dos implementaciones asimétricas (Priority: P1)

Entrada vacía "" → 422 (Pydantic `min_length=1`); "   " pasa Pydantic y muere en el comando → 400 (C-03). `NotFoundError` → 404 con `detail=str(exc)` y `ValueError` → 400 con `detail=str(exc)` en ambas rutas; excepción no prevista → `/chat` 500 con `detail=str(exc)` (expone el texto interno) vs `/predict` 500 plano "Internal Server Error" sin JSON (C-04/A-27/A-28).

**Why this priority**: es el contrato que ve cualquier cliente ante un fallo; su asimetría está congelada.

**Independent Test**: `tests/test_c03_validacion_vacia.py`, `tests/test_c04_errores_http.py`.

**Acceptance Scenarios**:

1. **Given** `{"query": ""}` en `/chat`, **When** se envía, **Then** 422 (Pydantic).
2. **Given** `{"query": "   "}`, **When** se envía, **Then** 400 con `{"detail": "query_text must not be empty"}` (pasa Pydantic, muere en el comando).
3. **Given** un fallo RuntimeError en `/chat`, **When** se procesa, **Then** 500 con `{"detail": "fallo interno de BD"}` (texto expuesto); en `/predict`, **Then** 500 en texto plano "Internal Server Error" sin JSON.

---

### User Story 2 - Configuración por entorno con credenciales solo locales (Priority: P1)

La configuración vive en Settings de pydantic-settings con `.env`; valores por defecto: `database_url=postgresql+asyncpg://weather:weather@localhost:5432/weather_agent`, `llm_api_url=https://opencode.ai/zen/go/v1`, `llm_model=mimo-v2.6-flash`, `open_meteo_base_url=https://api.open-meteo.com`, `model_path=models/model.pkl`, `embedder_model=all-MiniLM-L6-v2`, `debug=False`. Credenciales `weather`/`weather` SOLO para entorno local; prohibido producción sin override (acta P6; checklist de despliegue H13) (A-09).

**Why this priority**: protege la postura de despliegue aceptada y el punto único de configuración.

**Independent Test**: evidencia de líneas (`settings.py:9-16`, `docker-compose.yml:6-8`); verificación contractual.

**Acceptance Scenarios**:

1. **Given** un arranque sin `.env`, **When** se carga la configuración, **Then** se usan los valores por defecto listados (incluidas credenciales locales).
2. **Given** un despliegue en producción, **When** se revisa, **Then** debe existir override de credenciales (condición del acta P6/H13).

---

### User Story 3 - Constantes de contrato duplicadas con convención declarada (Priority: P2)

La convención declarada es que settings es el único sitio (acta P18), pero hoy conviven: ruta del modelo en 3 valores (predictor `"models/model.pkl"`, handlers `"model.pkl"`, settings `"models/model.pkl"`, C-05); horizontes `[6,12,24]` repetidos en 5 sitios del servicio y `[6,12,24,48,72,168]` en el artefacto (C-06; lista oficial 6/12/24, acta P5); modelo de embeddings `"all-MiniLM-L6-v2"` en settings (sin consumidor) y adaptador; dimensión 384 en ORM e `init.sql`; LLM duplicado en settings y adaptador (C-10). Todo congelado tal cual; unificación en modernización.

**Why this priority**: evita que cambios "inofensivos" de constantes rompan el sistema silenciosamente.

**Independent Test**: `tests/test_c05_c06_c10_constantes.py`.

**Acceptance Scenarios**:

1. **Given** los tres sitios de la ruta del modelo, **When** se comparan, **Then** difieren tal cual está congelado (C-05).
2. **Given** la lista de horizontes, **When** se consultan API, comando, handlers y artefacto, **Then** API/comando/handlers fijan [6,12,24] y el artefacto [6,12,24,48,72,168] (C-06).

---

### User Story 4 - Persistencia: Alembic fuente de verdad, dos fábricas de sesión, tablas sin escritor (Priority: P2)

Alembic es la fuente de verdad del esquema; `init.sql` solo primer arranque; `db-sync` deprecado (A-17, acta P7). Dos fábricas de sesión conviven (C-08/A-15). `knowledge_base` (vector(384), índice ivfflat) es la única tabla usada en runtime; `forecasts`/`models` sin escritor (A-24 → SPEC-004).

**Why this priority**: gobierna cómo evolucionan los esquemas y evita desincronización.

**Independent Test**: evidencia (`init.sql:4-39`, `alembic/versions/821f93690b12_*.py:20`, `Makefile:41-53`, `session.py:11-50`, `knowledge_base_adapter.py:27-37`); persistencia real fuera de la suite.

**Acceptance Scenarios**:

1. **Given** un entorno nuevo, **When** se crea el esquema, **Then** la migración Alembic es la referencia canónica (decisión acta P7).
2. **Given** el adaptador RAG, **When** accede a BD, **Then** usa su propia `async_sessionmaker` con transacción por operación (C-08 congelado).

---

### User Story 5 - Seguridad interna, logs y dependencias (Priority: P2)

Sin autenticación: servicio interno en red de confianza (acta P4: aceptado); el 500 de `/chat` expone texto de excepciones: NO aceptado, a corregir en modernización (A-05). Logs internos de uso operativo: prompt completo a INFO, SQL completas con `DEBUG=true`; texto completo a DEBUG en modernización (A-32, acta P14). Python 3.8.10 EOL con migración aprobada en modernización; auditoría de CVEs trimestral por el equipo de desarrollo (acta P15); joblib/tqdm/asyncpg/alembic usados y no declarados (A-11); pytest 7.4 vs 8.3 resuelto con la suite actual (A-37).

**Why this priority**: postura de operación acordada con TI; sin comportamiento de negocio propio.

**Independent Test**: evidencia (`chat.py:79-84`, `predict.py:84-99`, `main.py:23-30`, `Makefile:9`, `ask_agent/handler.py:127,170,196-202`, `requirements.txt:1-33`); verificación contractual.

**Acceptance Scenarios**:

1. **Given** una petición sin credenciales, **When** llega a `/chat` o `/predict`, **Then** se procesa sin autenticación (servicio interno aceptado).
2. **Given** `DEBUG=true`, **When** se ejecuta el chat, **Then** las SQL completas van al log (comportamiento congelado).

---

### User Story 6 - Higiene del repositorio y código muerto inventariado (Priority: P3)

Código de dominio sin consumidor (`Forecast`, `WeatherInterpretationService`, `LocationQuery`, `MockLLM`, `NullLogger`, getters de puertos), migración fantasma `320b6a04018d_test_migration` en caché, `__pycache__` commiteados, docstrings que prometen adaptadores inexistentes (A-23/A-25/A-26). Carrera de carga del modelo: peticiones concurrentes pueden duplicar `load_model`; cada handler mantiene su copia (A-35). Todo se inventaría tal cual; limpieza en modernización.

**Why this priority**: inventario de protección, no comportamiento observable.

**Independent Test**: mapa-sistema §4 (zonas oscuras) + verificación de llamadas (arqueología 2026-11-14).

**Acceptance Scenarios**:

1. **Given** el repositorio actual, **When** se audita, **Then** los artefactos huérfanos listados siguen presentes tal cual (congelados por inventario).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mantener el contrato de errores HTTP compuesto tal cual (422/400/404/500 con las asimetrías C-03/C-04 congeladas).
- **FR-002**: El sistema DEBE cargar la configuración desde Settings con `.env` y los valores por defecto congelados; credenciales por defecto SOLO locales (acta P6, H13).
- **FR-003**: El sistema DEBE mantener las constantes de contrato en sus sitios actuales tal cual (C-05/C-06/C-10 congelados; convención settings único sitio decidida en acta P18 para modernización).
- **FR-004**: El esquema DEBE evolucionar vía Alembic (fuente de verdad, acta P7); `init.sql` solo primer arranque; `db-sync` deprecado (A-17).
- **FR-005**: El sistema DEBE operar sin autenticación como servicio interno (acta P4); la exposición de texto de excepciones en el 500 de `/chat` queda documentada como no aceptada a corregir (A-05).
- **FR-006**: El sistema DEBE registrar en logs lo que registra hoy (prompt completo a INFO; SQL con DEBUG) hasta modernización (A-32, acta P14).
- **FR-007**: El runtime y las dependencias DEBE mantenerse tal cual (Python 3.8.10, dependencias no declaradas) con auditoría trimestral y migración de runtime aprobada para modernización (A-36/A-11, acta P15).
- **FR-008**: El inventario de código muerto, huérfanos y docstrings engañosos DEBE documentarse tal cual (A-23/A-25/A-26).
- **FR-009**: La carrera de carga del modelo y la doble copia por handler DEBE documentarse tal cual (A-35).

### Key Entities

- **Settings**: punto único de configuración por entorno (base de datos, LLM, Open-Meteo, modelo, embeddings, debug).
- **Esquema de BD**: tablas `knowledge_base` (vector(384)), `forecasts`, `models`; migración Alembic `821f93690b12`.
- **Contrato de errores HTTP**: mapeo excepción → código/detalle por ruta (dos implementaciones congeladas).

## Success Criteria *(mandatory)*

- **SC-001**: los contratos de validación y errores HTTP congelados y en verde (`test_c03_validacion_vacia`, `test_c04_errores_http`).
- **SC-002**: las constantes duplicadas congeladas con sus valores exactos (`test_c05_c06_c10_constantes`).
- **SC-003**: las decisiones de plataforma citadas por acta (P4, P6, P7, P14, P15, P18) marcadas como simuladas pendientes de ratificación.
- **SC-004**: la persistencia real (C-08/C-09, A-10/A-14/A-15/A-16) documentada con evidencia y reconocida como fuera de la suite (requiere PostgreSQL).

## Assumptions

- PostgreSQL 16 con pgvector (imagen `pgvector/pgvector:pg16`) es la base de datos del sistema.
- El servicio se despliega solo en red de confianza (sin autenticación) durante la fase de protección.
- Decisiones de acta simulada pendientes de ratificación real.

## Fuera de alcance

- Comportamiento de negocio de los dominios (geocodificación, predicción, conversación, entrenamiento) → SPEC-001 a SPEC-004.
- Decisiones de producto (horizontes, ciudades, redondeo): solo se referencian aquí como constantes congeladas; su contrato vive en SPEC-002.
