# Feature Specification: SPEC-04 — Entrenamiento y ciclo de vida del artefacto ML (offline)

**Feature Branch**: `specs/004-entrenamiento-artefacto-ml` (sin rama git: hook `before_specify` saltado por decisión del usuario)

**Created**: 2026-11-14

**Status**: Draft

**Input**: Especificación inversa de `propuesta-particion-specs.md` (PARTE 2, SPEC-04). Spec de ingeniería inversa: documenta el comportamiento EXISTENTE del entrenamiento y el ciclo de vida del artefacto `models/model.pkl` (dataset, semántica de lags/targets, partición, constantes, identidad y reglas protegidas de regeneración). No es una feature nueva: es la especificación formal de lo que el sistema YA hace, para que sirva de contrato en la modernización.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Partición 80/20 "temporal" que en realidad es una partición por ciudades (Priority: P1)

El corte `int(len × 0.8)` sobre filas ordenadas por bloques de ciudad cae al final del bloque de Sydney: el test son solo São Paulo + Tokyo (RN-14/A-01; `train_model.py:166,169-171`). El `test_score` 0.3712878051017324 es R² ENTRE CIUDADES, no fiabilidad del servicio (prohibido citarlo como tal, R21, acta P1).

**Why this priority**: es el hallazgo de mayor impacto económico; su corrección (reentrenamiento) es la decisión central de modernización.

**Independent Test**: arqueología de datos (263.040 = 10×26.304; split_idx = 210.432 = 8 bloques exactos; OneHot de 8 ciudades) + `TestMetadatosDelModeloReal` (scores congelados).

**Acceptance Scenarios**:

1. **Given** el CSV actual, **When** se entrena con test_size=0.2, **Then** el test son solo las ciudades Tokyo y São Paulo y el `test_score` publicado es 0.3712878051017324 (tal cual, congelado).
2. **Given** la decisión acta P1/§8, **When** se modernice, **Then** se reentrena con split correcto y alineación de mercado (España/Madrid prioritario, cobertura global mantenida, español prioritario, ñ/ã soportadas).

---

### User Story 2 - Semántica de lags: h filas antes dentro de la ciudad (convención vigente) (Priority: P1)

El lag h es el valor de h FILAS antes dentro de cada ciudad (`groupby("city").shift(h)`), equivalente a h horas solo si el CSV es continuo (verificado: 0 huecos, 0 duplicados) (RN-15; convención declarada vigente de C-02; `train_model.py:100`). Esta es la convención que SPEC-002 debe alcanzar en runtime al alinearse (acta P2).

**Why this priority**: define el significado real de las variables que el modelo aprendió.

**Independent Test**: `tests/test_c02_entrenamiento_lags.py` (shift por ciudad, lag ≠ target, colas).

**Acceptance Scenarios**:

1. **Given** 20 filas por ciudad con valores 0..19, **When** se preparan targets a 6 y se ingenierizan lags a 6, **Then** para la fila original 6: `lag_6 == 0.0` (fila 0) y `target_6 == 12.0` (fila 12).
2. **Given** horizonte 168, **When** se preparan targets sobre un bloque de 20 filas, **Then** ninguna fila tiene objetivo (colas perdidas, RN-16).

---

### User Story 3 - Constantes de entrenamiento fijas y semilla (Priority: P2)

200 árboles, profundidad 5, tasa 0.1, submuestreo 0.8, semilla 42; horizontes [6,12,24,48,72,168] (RN-17; `train_model.py:155,186-193`).

**Why this priority**: determinismo del entrenamiento y reproducibilidad del activo.

**Independent Test**: `tests/test_c02_entrenamiento_lags.py::TestRN17ConstantesDeEntrenamiento` (firma y fuente congeladas).

**Acceptance Scenarios**:

1. **Given** dos entrenamientos con el mismo CSV, **When** se comparan, **Then** producen el mismo modelo (semilla explícita), salvo cambios de entorno.

---

### User Story 4 - Regla protegida: el wrapper vive picklado como `__main__` (Priority: P1)

`MultiOutputRegressorWithProgress` vive picklada como `__main__` dentro de `model.pkl`; moverla inutiliza el activo; el predictor reescribe `sys.modules["__main__"]` al cargar (A-21; H4/W1/W2; `local_predictor.py:21-31`, `model_wrapper.py`). Propietario nominal: Marta Ruiz, equipo de datos/ML (acta §8, simulada); cualquier cambio del wrapper exige reentrenamiento coordinado.

**Why this priority**: restricción dura que protege el activo de negocio de 3,6 MB.

**Independent Test**: carga real del artefacto en `tests/conftest.py` + `TestMetadatosDelModeloReal` (la suite entera depende de esta regla).

**Acceptance Scenarios**:

1. **Given** el binario actual, **When** se carga con el predictor, **Then** deserializa porque la clase está registrada como `__main__.MultiOutputRegressorWithProgress`.
2. **Given** una modificación del wrapper sin reentrenamiento, **When** se intenta cargar el artefacto, **Then** falla (regla protegida con incidente histórico).

---

### User Story 5 - Identidad del artefacto y esquema congelado (Priority: P2)

Versión = md5 truncado del binario (actual `b59e0918`), fecha = mtime (RN-12/A-22; acta P10: provisional). Esquema: 44 feature_columns (7 temporales + 6 variables × 6 horizontes + city), 36 target_columns, OneHot de 8 ciudades, scores 0.5431063937097727 / 0.3712878051017324 (A-38: sin dew_point/wind_direction).

**Why this priority**: trazabilidad del activo y contrato de forma del artefacto.

**Independent Test**: `TestMetadatosDelModeloReal` + `model_version` congelado en el golden master.

**Acceptance Scenarios**:

1. **Given** una copia idéntica del binario, **When** se consulta la versión, **Then** es la misma (md5 del contenido); tocando el fichero cambia mtime pero no la versión.
2. **Given** el artefacto actual, **When** se inspecciona, **Then** `horizons == [6,12,24,48,72,168]` y las feature_columns no contienen `dew_point` ni `wind_direction`.

---

### User Story 6 - Tablas forecasts/models y métricas (Priority: P3)

Tabla `forecasts` = requisito pendiente (histórico consultable de predicciones, acta P11); tabla `models` = descartada (acta P11: las métricas viajan en el artefacto). Si una variable no varía en test, su R² se publica como 0 (RN-18/A-40; `train_model.py:227-228`).

**Why this priority**: decisiones de alcance de persistencia y convención de métricas.

**Independent Test**: evidencia de esquema (`init.sql:4-39`, ORM sin escritores); convención R² por revisión de línea.

**Acceptance Scenarios**:

1. **Given** el esquema actual, **When** se revisa, **Then** `forecasts` y `models` existen sin ningún código que escriba o lea (A-24 congelado).

---

### Edge Cases

- Horizonte 168 sin objetivo en bloques cortos (colas descartadas, RN-16).
- Variable constante en test → R² publicado como 0, no "no calculable" (A-40).
- Ciudad con acentos en el dataset ("São Paulo" con acento y tilde viaja tal cual al codificador, RN-07).
- CSV continuo verificado (0 huecos/0 duplicados): si dejara de serlo, los lags por filas dejarían de ser horas (RN-15).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El entrenamiento DEBE partir el dataset con `int(len × 0.8)` truncado, sin shuffle, en el orden del fichero (comportamiento crítico congelado; A-01; reentrenamiento decidido en acta P1/§8).
- **FR-002**: Los lags DEBE construirse con `groupby("city").shift(h)` (h filas antes) y los targets con `shift(-h)` (colas descartadas) (RN-15/RN-16; convención vigente de C-02).
- **FR-003**: El entrenamiento DEBE usar las constantes fijas: n_estimators=200, max_depth=5, learning_rate=0.1, subsample=0.8, random_state=42, horizontes [6,12,24,48,72,168] (RN-17).
- **FR-004**: El artefacto DEBE mantener el wrapper `MultiOutputRegressorWithProgress` picklado como `__main__`; su modificación exige aprobación del propietario nominal y reentrenamiento (A-21, regla protegida H4/W1/W2, acta §8).
- **FR-005**: La identidad del artefacto DEBE ser md5 truncado + mtime hasta la modernización (RN-12/A-22, acta P10).
- **FR-006**: El esquema del artefacto DEBE mantenerse congelado: 44 features, 36 targets, OneHot de 8 ciudades (verificado por tests y golden master).
- **FR-007**: El próximo reentrenamiento DEBE incluir la alineación de mercado decidida (acta §8: España/Madrid prioritario, cobertura global, español prioritario, ñ/ã) (A-41).
- **FR-008**: El R² de variable constante DEBE publicarse como 0 tal cual (A-40).
- **FR-009**: La tabla `forecasts` DEBE tratarse como requisito pendiente y `models` como descartada (acta P11; A-24).

### Key Entities

- **model.pkl**: pipeline (ColumnTransformer + wrapper multi-salida), feature/target columns, horizontes, scores, OneHot de 8 ciudades.
- **historical_weather.csv**: 263.040 filas, 10 ciudades × 26.304 horas (2023-2025), UTC verificado, orden por bloques de ciudad.
- **MultiOutputRegressorWithProgress**: clase envoltorio picklada como `__main__` (contrato binario protegido).

## Success Criteria *(mandatory)*

- **SC-001**: la semántica de lags/targets congelada y en verde (`test_c02_entrenamiento_lags`).
- **SC-002**: el esquema del artefacto y su identidad congelados (`TestMetadatosDelModeloReal`, `model_version` en el master).
- **SC-003**: A-01/A-04 documentados con su tratamiento de modernización y la prohibición de citar 0,37 (R21) incluida en la spec.
- **SC-004**: la regla protegida A-21 citada con su incidente histórico (H4/W1/W2) y propietario nominal (acta §8, pendiente de ratificación).

## Assumptions

- El CSV `data/historical_weather.csv` continúa continuo y en UTC durante la fase de protección.
- El reentrenamiento (A-01/A-41) ocurre en modernización, no durante la protección.
- Decisiones de acta simulada (P1, P2, P9, P10, P11, §8) pendientes de ratificación real.

## Fuera de alcance

- Consumo del artefacto en runtime (`/predict`) → SPEC-002.
- Descarga del histórico desde Open-Meteo archive (servicio) → SPEC-001; la descarga del dataset vive aquí como proceso offline.
- Cualquier capa HTTP o configuración transversal → SPEC-005.
