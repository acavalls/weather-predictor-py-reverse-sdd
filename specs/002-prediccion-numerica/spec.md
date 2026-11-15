# Feature Specification: SPEC-02 — Contrato de predicción numérica (`/predict` y modelo en runtime)

**Feature Branch**: `specs/002-prediccion-numerica` (sin rama git: hook `before_specify` saltado por decisión del usuario)

**Created**: 2026-11-14

**Status**: Draft

**Input**: Especificación inversa de `propuesta-particion-specs.md` (PARTE 2, SPEC-02). Spec de ingeniería inversa: documenta el comportamiento EXISTENTE del contrato de predicción numérica (endpoint `/predict` y modelo en runtime). No es una feature nueva: es la especificación formal de lo que el sistema YA hace, para que sirva de contrato en la modernización.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - `/predict` devuelve predicciones a 6/12/24 h con nombres por convención (Priority: P1)

El negocio pide la predicción de una ciudad y recibe, por cada horizonte, las 6 variables meteorológicas con claves `{variable}_target_{horizonte}` (RN-06/RN-11; `local_predictor.py:215-229`, `predict.py:32-35`). El modelo entrenó además 48/72/168, no expuestos (acta P5: horizontes oficiales 6/12/24).

**Why this priority**: es el contrato numérico principal del producto; el golden master lo congela por completo.

**Independent Test**: `tests/golden_master/master.json` (12 casos) + `tests/test_rn05_rn06_rn07_predictor.py`. Regeneración del master solo con decisión de negocio documentada (`tests/golden_master/LEEME.md`).

**Acceptance Scenarios**:

1. **Given** Madrid con condiciones estándar el viernes 15-03-2024 14:00 UTC, **When** se predice a [6,12,24], **Then** `predictions[6]["temperature_2m"] == 18.178030264044768` y las claves siguen el patrón `{variable}_target_{horizonte}`.
2. **Given** `{"horizons": [6, 999]}`, **When** se predice, **Then** 999 se descarta sin aviso y solo se devuelve 6 (RN-05/A-07).
3. **Given** `{"horizons": [999]}`, **When** se predice, **Then** `ValueError("Prediction result must contain at least one prediction")` → HTTP 400 con ese texto interno (RN-05/A-07).

---

### User Story 2 - Ciudades fuera del OneHot se codifican a ceros (comportamiento congelado) (Priority: P2)

El codificador solo conoce 8 ciudades; Tokyo, São Paulo o cualquier otra se codifican a ceros y sus predicciones difieren mínimamente (A-02). Política ratificada (acta P8/§8): solo las ciudades entrenadas están soportadas oficialmente (A-20).

**Why this priority**: comportamiento documentado como BUG HISTÓRICO CON DEPENDIENTES; su corrección va ligada al reentrenamiento de SPEC-004.

**Independent Test**: `tests/test_rn05_rn06_rn07_predictor.py::TestA02CiudadesFueraDelOneHot` y casos `tokyo_fuera_onehot`/`sao_paulo_fuera_onehot`/`atlantis_inexistente` del golden master.

**Acceptance Scenarios**:

1. **Given** las mismas condiciones para Madrid y Tokyo, **When** se predice a 6 h, **Then** Madrid `relative_humidity_2m == 60.13257982269474` y Tokyo `== 60.92908951903441` (única diferencia); 12/24 h idénticas.
2. **Given** la ciudad "Atlantis" (no está en ninguna categoría), **When** se predice, **Then** recibe la misma codificación a ceros que Tokyo.

---

### User Story 3 - Los lags valen el tiempo actual (aproximación provisional) (Priority: P2)

En runtime, el valor de entrada para cualquier horizonte h es siempre la condición actual (RN-08/A-04; `feature_extractor.py:62-77`); la semántica de entrenamiento usa el valor de h filas antes (SPEC-004, convención vigente de C-02). Tratamiento acta P2: aproximación provisional, alinear antes de reentrenar.

**Why this priority**: afecta a la calidad de toda predicción servida; está congelado tal cual.

**Independent Test**: `tests/test_rn07_rn08_rn09_feature_extractor.py::TestRN08LagsValenElTiempoActual`.

**Acceptance Scenarios**:

1. **Given** 18,5 °C actuales, **When** el extractor construye lags para [6,12,24], **Then** `temperature_2m_lag_6/_12/_24 == 18.5` (idénticos entre sí).

---

### User Story 4 - La predicción de un horizonte depende de los horizontes pedidos (Priority: P2)

Pedir menos horizontes cambia la predicción de los que se conservan, porque los lags de los horizontes no pedidos entran a 0.0 en el alineado (A-43, hallazgo de la caracterización). Congelado tal cual.

**Why this priority**: comportamiento sorprendente que un cliente podría descubrir; protegerlo evita cambios accidentales.

**Independent Test**: `tests/test_rn05_rn06_rn07_predictor.py::TestA43PrediccionDependeDeLosHorizontesPedidos` y casos `madrid_solo_h6`/`madrid_horizontes_mixtos` del master.

**Acceptance Scenarios**:

1. **Given** Madrid, mismas condiciones, **When** se pide solo `[6]`, **Then** temperatura a 6 h `== 4.250787940828976`; con `[6,12,24]`, `== 18.178030264044768`.

---

### User Story 5 - Sin redondeos y con identidad del modelo servida (Priority: P3)

Las salidas llevan todos los decimales que produce el modelo (RN-13/A-39; decisión acta §8: sin redondeo es contrato oficial). La identidad del modelo es md5 truncado + mtime (RN-12/A-22; acta P10: provisional; actual: `b59e0918`).

**Why this priority**: estabiliza el formato de salida y la trazabilidad del activo.

**Independent Test**: valores completos del golden master; identidad congelada en `TestMetadatosDelModeloReal`.

**Acceptance Scenarios**:

1. **Given** una predicción con decimales largos, **When** se sirve, **Then** no se redondea ni trunca (p. ej. 18.5343994140625 saldría tal cual).
2. **Given** el artefacto actual, **When** se consulta la versión, **Then** es `b59e0918` (md5 del binario truncado) y la fecha es el mtime.

---

### Edge Cases

- Extremos físicos aceptados como entrada del modelo: temperatura -40, presión 870, humedad 0, nubes 100 (caso `madrid_extremos_fisicos` del master).
- Ciudad con acento y tilde viaja tal cual al codificador ("São Paulo", RN-07).
- Lags de viento/rocío siempre a 0 en inferencia (RN-09/A-38): el extractor los calcula y el modelo ni los consume (44 columnas sin `dew_point`/`wind_direction`).
- Ruta del modelo: tres valores conviven (A-06/C-05): predictor `"models/model.pkl"`, handlers `"model.pkl"`, settings `"models/model.pkl"`.
- Prohibición de comunicación (R21, acta P1): el `test_score` 0.3713 NO se presenta como fiabilidad del producto (es R² entre ciudades).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE exponer por API solo los horizontes 6/12/24 h (valores por defecto y de ejemplo) aunque el modelo entrenó 6 más. Evidencia: `predict.py:32-35`, `command.py:19`, `ask_agent/handler.py:160,165`.
- **FR-002**: El sistema DEBE descartar sin aviso los horizontes que el modelo no conoce y DEBE fallar con `ValueError("Prediction result must contain at least one prediction")` si no queda ninguno. Evidencia: `local_predictor.py:215-229`, `ml/value_objects/__init__.py:126`.
- **FR-003**: El sistema DEBE nombrar la salida `{variable}_target_{horizonte}` y parsearla con `rsplit("_target_", 1)`. Evidencia: `train_model.py:125-131`, `local_predictor.py:215-229`.
- **FR-004**: El sistema DEBE alinear las entradas al esquema del modelo: columnas ausentes → 0.0, extra → descartadas, `city` con el nombre tal cual. Evidencia: `local_predictor.py:186-192`.
- **FR-005**: El sistema DEBE rellenar todos los lags con la condición actual (aproximación provisional, acta P2). Anomalía: A-04.
- **FR-006**: El sistema DEBE codificar a ceros toda ciudad fuera del OneHot y DEBE documentar que solo las ciudades entrenadas están soportadas (acta P8/§8). Anomalías: A-02/A-20.
- **FR-007**: El sistema DEBE producir salidas sin redondeo (acta §8) y DEBE servir la identidad md5+mtime como versión (acta P10).
- **FR-008**: El sistema DEBE comportarse igual ante horizontes parciales tal cual está congelado (A-43); su corrección solo procede en modernización.

### Key Entities

- **PredictionResult**: `predictions` anidado `{horizonte: {variable: valor}}`, versión del modelo e instante de predicción; exige al menos una predicción.
- **FeatureSet**: 31 features para [6,12,24] (7 temporales + 8 lags × 3) + ciudad; el alineado la ajusta a las 44 columnas del modelo.

## Success Criteria *(mandatory)*

- **SC-001**: el golden master de 12 casos regenera idéntico (verde en `tests/test_golden_master.py`); cualquier divergencia exige investigación y decisión de negocio documentada antes de regenerar.
- **SC-002**: 100 % de los umbrales de horizontes congelados: `[6]`, `[6,999]`, `[999]`, `[6,12,24]`, y horizontes entrenados (6,12,24,48,72,168) verificables por test.
- **SC-003**: la política de ciudades (A-20) y la identidad del modelo (A-22) citan su acta y quedan marcadas como provisionales hasta ratificación real.

## Assumptions

- El artefacto `models/model.pkl` (md5 `b59e0918`) no cambia durante la fase de protección; si cambia, el master debe regenerarse como parte de la misma decisión documentada.
- Decisiones de acta simulada (P1, P2, P5, P8, P10, P16, §8) pendientes de ratificación real.

## Fuera de alcance

- Geocodificación y magnitudes del tiempo → SPEC-001.
- Uso conversacional de la predicción (incluida su ruta de características a ceros, A-03) → SPEC-003.
- Entrenamiento y regeneración del artefacto → SPEC-004.
- Configuración, errores HTTP y persistencia transversales → SPEC-005.
