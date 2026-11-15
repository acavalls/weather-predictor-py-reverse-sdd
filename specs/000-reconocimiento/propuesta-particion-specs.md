# Propuesta de partición del sistema en specs formales

Documento de decisión, pendiente de revisión y aprobación. NO ejecuta
ningún `/speckit.specify`: la partición se aprueba antes de invertir.

**Precondición verificada**: la lista PENDIENTE del registro de anomalías
está **vacía** tras la ronda 2 del acta (`acta-entrevista-negocio.md` §8,
2026-11-14). **Advertencia constitucional**: tanto la ronda 1 como la 2
del acta son **simuladas**; ninguna decisión de negocio computa como
testigo válido hasta su ratificación real por personas identificadas
(Principio II). La ejecución de las specs debe ir acompañada de esa
ratificación.

Fuentes leídas al completo: `mapa-sistema.md`, `flujo-aplicacion.md`,
`reglas-de-negocio.md` (RN-01..RN-28), `contradiccion-01..10-*.md`,
`registro-riesgos.md` (R1-R21), `memoria-historica.md` (H1-H14, W1-W4),
`registro-de-anomalias.md` (A-01..A-43), `acta-entrevista-negocio.md`
(P1-P18 + §8) y la suite de caracterización `tests/` (190 tests, commit
`3035256`).

---

## PARTE 1 — La partición

Cinco dominios de negocio. Cada uno es un conjunto de reglas que el
negocio decide junto y que puede evolucionar sin arrastrar a los demás.
El criterio de reparto de contradicciones aplicado: la **convención
declarada vigente** va a la spec del dominio que posee la regla; la
implementación divergente se referencia como anomalía en la spec del
camino que la usa.

```text
SPEC-01 Datos meteorológicos en tiempo real
   └─ alimenta a ▼
SPEC-02 Contrato de predicción numérica (/predict y modelo en runtime)
   └─ consume el artefacto generado por ▼
SPEC-04 Entrenamiento y ciclo de vida del artefacto ML (offline)
SPEC-03 Agente conversacional (/chat: lenguaje, contexto, LLM)
   └─ usa SPEC-01 y SPEC-02 como proveedores de contexto
SPEC-05 Plataforma y operación (config, errores HTTP, persistencia, higiene)
   └─ transversal: sirve a 01-04
```

### SPEC-01 — Datos meteorológicos en tiempo real

- **Alcance**: cómo el sistema resuelve una ciudad a coordenadas, qué
  magnitudes del tiempo acepta como válidas y qué hace cuando una
  magnitud no llega. Es el contrato de entrada del dato meteorológico
  para todo el sistema.
- **Módulos**: `src/domain/weather/value_objects/__init__.py`,
  `src/domain/weather/repository/__init__.py` (puerto + `CurrentWeather`),
  `src/infrastructure/weather/open_meteo_adapter.py`.
- **Reglas**: RN-01 (geocodificación: primer resultado, `count=1`,
  `language=en`), RN-02 (ciudad desconocida → `NotFoundError` → 404),
  RN-03 (magnitud ausente → 0 / 1013 hPa), RN-04 (límites físicos con
  fronteras inclusivas: temperatura [-100, 100] °C, humedad [0, 100] %,
  presión [870, 1084] hPa, precipitación/viento ≥ 0, nubes [0, 100] %,
  lat [-90, 90], lon [-180, 180]).
- **Anomalías**: ninguna propia (RN-03 es DUDOSA y se pregunta en la spec
  como decisión ratificable, no como bug).
- **Tests**: `tests/test_rn04_value_objects.py` (fronteras completas).
  RN-01/RN-02/RN-03 quedan **fuera de la red** (IO de red); su
  verificación será contractual (no ejecutable sin Open-Meteo).
  Golden master: lo cubre indirectamente (el proveedor fijo del master
  respeta RN-04).
- **Dueño natural**: responsable del producto (acta P8) con TI para RN-03
  (acta P4 no cubre defaults: queda como decisión a ratificar).

### SPEC-02 — Contrato de predicción numérica (`/predict` y modelo en runtime)

- **Alcance**: qué devuelve `POST /predict`, cómo se convierten las
  condiciones actuales en características del modelo, qué horizontes
  existen, cómo se nombra la salida y qué identidad tiene el modelo
  servido. Es el contrato numérico de negocio.
- **Módulos**: `src/application/predict/handler.py`,
  `src/application/predict/command.py`,
  `src/infrastructure/http/routes/predict.py`,
  `src/infrastructure/ml/feature_extractor.py`,
  `src/infrastructure/ml/local_predictor.py`.
- **Reglas**: RN-05 (solo horizontes entrenados; descarte silencioso),
  RN-06 (nombres `{variable}_target_{horizonte}`), RN-07 (alineación:
  ausentes → 0.0, sobrantes fuera, ciudad como texto), RN-08 (los lags
  valen el tiempo actual), RN-09 (viento/rocío a 0 en inferencia),
  RN-11 (API expone solo 6/12/24 h), RN-13 (sin redondeos en la salida;
  decisión acta §8).
- **Anomalías** (clasificación / tratamiento): A-07 (BUG A SECAS /
  validar en modernización), A-08 (INTENCIONAL* / especificar tal cual:
  horizontes oficiales 6/12/24), A-43 (BUG A SECAS / especificar tal
  cual, congelado), A-06 (BUG A SECAS / unificar en modernización),
  A-38 (ACCIDENTAL / documentar sin especificar), A-39 (ACCIDENTAL /
  decisión acta §8: sin redondeo es contrato oficial), A-02 (BUG
  HISTÓRICO CON DEPENDIENTES / corregir con reentrenamiento A-01;
  mecanismo referenciado), A-20 (INTENCIONAL* / política: solo ciudades
  entrenadas soportadas), A-04 (BUG HISTÓRICO CON DEPENDIENTES /
  aproximación provisional, alineación con SPEC-04).
- **Tests**: `tests/test_rn05_rn06_rn07_predictor.py`,
  `tests/test_rn07_rn08_rn09_feature_extractor.py` (lado runtime).
  **Golden master: lo cubre por completo** (12 casos: ciudades OneHot y
  fuera, chat-ceros, horizontes [6]/[6,999]/[6,12,24], extremos físicos,
  sábado/29-feb/fin de año).
- **Dueño natural**: responsable del producto de predicción (acta P1,
  P2, P5, P16).

### SPEC-03 — Agente conversacional (`/chat`)

- **Alcance**: cómo el sistema entiende la pregunta del usuario
  (intención y ciudad), qué contexto reúne (tiempo, predicción, RAG),
  cómo compone el prompt y qué parámetros usa ante el LLM. Incluye el
  ciclo de vida de la sesión y sus eventos.
- **Módulos**: `src/application/ask_agent/handler.py`,
  `src/application/ask_agent/command.py`,
  `src/domain/agent/aggregate/__init__.py`,
  `src/domain/agent/value_objects/{query_intent,context_chunk,retrieved_document}.py`,
  `src/infrastructure/llm/opencode_go_llm.py`,
  `src/infrastructure/http/routes/chat.py`,
  `src/infrastructure/embedding/local_embedder.py`,
  `src/infrastructure/persistence/knowledge_base_adapter.py`.
- **Reglas**: RN-19 (intención por subcadenas, orden fijo), RN-20
  (pregunta general: sin tiempo/modelo, con RAG+LLM), RN-21 (histórico
  responde como tiempo actual), RN-22 (ciudad con patrones
  in/at/for/en), RN-23 (RAG siempre, top-3, sin umbral), RN-24 (una
  pregunta y una respuesta), RN-25 (prompt: system + contexto + query),
  RN-26 (sesión LLM compartida, temperatura 0.7, 1024 tokens), RN-27
  (eventos que se pierden), RN-10 (chat entrega condiciones nulas).
- **Anomalías**: A-03 (BUG A SECAS / corregir en modernización; camino
  que usa la implementación divergente de C-01), A-12 (BUG A SECAS /
  caracterizar), A-18 (BUG A SECAS / especificar tal cual), A-29
  (ACCIDENTAL / especificar tal cual), A-30 (INTENCIONAL* /
  provisional; histórico en deseos), A-31 (INTENCIONAL* / umbral en
  modernización), A-33 (BUG A SECAS / caracterizar y corregir), A-42
  (BUG A SECAS / corregir en modernización; congelado), A-19
  (INTENCIONAL* / contrato aportado acta §8).
- **Tests**: `tests/test_rn19_query_intent.py`,
  `tests/test_rn22_city_extraction.py`,
  `tests/test_rn24_rn27_chat_session.py`,
  `tests/test_rn25_rn13_prompt_summary.py` (prompt),
  `tests/test_c01_conversion_duplicada.py` (camino chat),
  `tests/test_c03_validacion_vacia.py`, `tests/test_c04_errores_http.py`
  (contrato /chat). RAG real (Búsqueda vectorial) **fuera de la red**.
- **Dueño natural**: responsable del producto (acta P5, P8, P12, P13)
  con compras para A-19 (acta P3, §8).

### SPEC-04 — Entrenamiento y ciclo de vida del artefacto ML (offline)

- **Alcance**: cómo se genera `models/model.pkl`: dataset, semántica de
  lags y targets, partición, constantes de entrenamiento, identidad del
  artefacto y reglas protegidas de regeneración. Es el dominio del
  equipo de datos/ML.
- **Módulos**: `scripts/train_model.py`,
  `scripts/download_historical.py`, `data/historical_weather.csv`,
  `models/model.pkl`, `src/infrastructure/ml/model_wrapper.py`.
- **Reglas**: RN-14 (partición 80/20 truncada), RN-15 (lags por filas
  desplazadas; convención declarada vigente de C-02), RN-16 (targets h
  filas después; colas perdidas), RN-17 (200 árboles, profundidad 5,
  tasa 0.1, submuestreo 0.8, semilla 42), RN-12 (identidad md5+mtime;
  convención vigente de C-05 en el artefacto).
- **Anomalías**: A-01 (BUG HISTÓRICO CON DEPENDIENTES / reentrenar en
  modernización con split correcto y alineación de mercado, acta §8),
  A-21 (INTENCIONAL* / restricción dura: propietario nominal Marta
  Ruiz, acta §8), A-22 (INTENCIONAL* / provisional; versión real en
  modernización), A-24 (INTENCIONAL* / `forecasts` requisito pendiente,
  `models` descartada), A-40 (ACCIDENTAL / documentar), A-41
  (INTENCIONAL* / alineación decidida, acta §8).
- **Tests**: `tests/test_c02_entrenamiento_lags.py` (semántica shift y
  targets), metadatos del artefacto en
  `tests/test_rn05_rn06_rn07_predictor.py`
  (`TestMetadatosDelModeloReal`), `model_version` congelado en el
  golden master. El entrenamiento completo **queda fuera de la red**.
- **Dueño natural**: equipo de datos/ML (acta P9, §8: Marta Ruiz,
  simulada).

### SPEC-05 — Plataforma y operación (transversal)

- **Alcance**: los contratos que no pertenecen a un solo dominio:
  configuración y constantes, contratos de error HTTP comunes,
  persistencia y esquema de BD, credenciales, dependencias, runtime,
  logs e higiene del repositorio. Es la spec que protege "cómo está
  montado" sin decidir comportamiento de negocio.
- **Módulos**: `src/infrastructure/config/{di,settings}.py`,
  `src/infrastructure/persistence/*`,
  `src/infrastructure/logging/*`, `docker-compose.yml`, `init.sql`,
  `alembic/`, `Makefile`, `requirements.txt`, `pyproject.toml`.
- **Reglas**: no posee RN-* propias; absorbe los contratos duplicados
  como índice: C-03 (validación vacía en dos capas), C-04 (mapeo de
  errores asimétrico), C-08 (sesiones de BD), C-10 (constantes
  duplicadas), C-09 (búsqueda vectorial, referencia).
- **Anomalías**: A-05 (INTENCIONAL* auth + BUG A SECAS detalle de
  error), A-09 (INTENCIONAL* solo local + checklist), A-10 (BUG A SECAS
  / transacción única), A-11 (BUG A SECAS / declarar dependencias),
  A-13 (ACCIDENTAL / unificar), A-14 (ACCIDENTAL / documentar), A-15
  (ACCIDENTAL / documentar), A-16 (ACCIDENTAL / documentar), A-17
  (INTENCIONAL* / Alembic fuente de verdad), A-23 (ACCIDENTAL /
  documentar), A-25 (ACCIDENTAL / limpieza), A-26 (ACCIDENTAL /
  documentar), A-27 (ACCIDENTAL / contrato único), A-28 (ACCIDENTAL /
  contrato único), A-32 (INTENCIONAL* / logs internos; texto a DEBUG),
  A-34 (ACCIDENTAL / documentar), A-35 (ACCIDENTAL / documentar), A-36
  (INTENCIONAL* / auditoría trimestral + migrar 3.8), A-37 (ACCIDENTAL
  / resolver versiones ya resuelto con `tests/`).
- **Tests**: `tests/test_c03_validacion_vacia.py`,
  `tests/test_c04_errores_http.py`,
  `tests/test_c05_c06_c10_constantes.py`.
- **Dueño natural**: TI/infraestructura (acta P4, P6, P7, P14, P15).

### Reparto de contradicciones (C-01..C-10)

| C | Convención declarada vigente → spec | Implementación divergente → spec usuaria |
|---|---|---|
| C-01 | `_weather_to_conditions` (claves Open-Meteo) → SPEC-02 | `to_features()` usada por el chat → anomalía A-03 en SPEC-03 |
| C-02 | Semántica de entrenamiento `shift(h)` (RN-15) → SPEC-04 | Lags = valor actual en runtime (RN-08) → anomalía A-04 en SPEC-02 |
| C-03 | Ambas capas son vigentes (comportamiento compuesto) → SPEC-05 | — |
| C-04 | Contrato de errores por ruta → SPEC-05 (asimetría congelada) | — |
| C-05 | `models/model.pkl` (predictor + settings) → SPEC-02/05 | `model.pkl` en handlers → SPEC-05 (referencia), congelado |
| C-06 | Lista oficial 6/12/24 (acta P5) → SPEC-02 | Copias literales en handlers/rutas → SPEC-05 |
| C-07 | Convención "todo por settings" (acta P18) → SPEC-05 | Script de ingesta con su propia instancia → SPEC-05 |
| C-08 | `get_session_factory` (docstring FastAPI) → SPEC-05 | `async_sessionmaker` propia del adaptador → SPEC-05 |
| C-09 | Adaptador async (binding, validación [0,1]) → SPEC-03/05 | Búsqueda del script de ingesta → SPEC-05 |
| C-10 | Settings como único sitio (acta P18) → SPEC-05 | Defaults y constantes locales → SPEC-05 |

### Casos frontera (con recomendación y criterio)

1. **RN-22/A-42 (extracción de ciudad)**: podría ir a SPEC-01 (resuelve
   una ubicación) o SPEC-03 (parsea lenguaje). → **SPEC-03**. Criterio:
   la regla decide sobre el texto del usuario, no sobre el servicio de
   geocodificación; SPEC-01 consume su resultado.
2. **A-20 (ciudades fuera del dataset)**: mecanismo de codificación
   (SPEC-02) vs política de soporte (P8, podría ir a SPEC-01). →
   **SPEC-02**. Criterio: la consecuencia observable es la predicción
   con codificación a ceros; la política solo tiene sentido como parte
   del contrato de predicción.
3. **RN-13/A-39 (sin redondeos)**: afecta a la salida de ambos endpoints.
   → **SPEC-02** (dueño del contrato numérico), con referencia cruzada
   desde SPEC-03 (resumen del chat usa el mismo principio). Criterio:
   evitar dos specs con la misma regla de presentación.
4. **RN-12/A-22 (identidad del modelo)**: el artefacto (SPEC-04) genera
   la identidad; `/predict` la publica. → **SPEC-04** define, SPEC-02
   referencia. Criterio: el dominio posee el activo.
5. **A-33 (similitud RAG sin acotar)**: bug del adaptador (SPEC-05) o
   modo de fallo del chat (SPEC-03)? → **SPEC-03**. Criterio: se
   manifiesta como fallo 400 de `/chat`; el adaptador se documenta en
   SPEC-05.
6. **A-18/RN-27 (eventos de sesión)**: agregado de dominio vs flujo del
   chat. → **SPEC-03**. Criterio: los eventos nacen y mueren dentro del
   flujo conversacional.
7. **A-06 (ruta del modelo)**: contrato de configuración (SPEC-05) o de
   predicción (SPEC-02)? → **SPEC-02** lo congela como parte del
   contrato de carga del modelo; SPEC-05 referencia C-05. Criterio:
   la divergencia muerde al construir handlers de predicción.

### Completitud y exclusiones

- **RN-01..RN-27**: asignados (ver tabla resumen). **RN-28**: EXCLUIDA
  con justificación: **refutada por la arqueología de datos** (el CSV es
  UTC en las 10 ciudades; entrenamiento e inferencia alineados). No es
  regla vigente ni anomalía; consta como corrección en el registro.
- **A-01..A-43**: todas asignadas (ver tabla resumen).
- **Riesgos R1-R21 sin comportamiento de negocio propio**: no generan
  spec (son causas o consecuencias de anomalías ya asignadas); los
  tratamientos viajan con su anomalía. R20 (presupuesto LLM) y R21 (no
  citar el 0,37) se citan en SPEC-03 y SPEC-04 respectivamente como
  restricciones de comunicación/operación.
- **Memoria histórica (H1-H14, W1-W4)**: contexto, no requisitos; se
  cita como evidencia dentro de las specs donde la regla protegida
  aplica (H3/W3 → SPEC-03 vía A-19; H4/W1/W2 → SPEC-04 vía A-21).
- **Zonas muertas del dominio (`Forecast`, `WeatherInterpretationService`,
  `LocationQuery`, `MockLLM`)**: sin comportamiento observable en
  runtime → SPEC-05 (higiene, A-23) como inventario a proteger, no como
  contrato de negocio.

### Criterio de tamaño

Cinco specs, estimadas entre 8 y 18 requisitos cada una: revisables por
el negocio en una sentada (~30 min). No hay pares que se citen
mutuamente en más de la mitad de sus requisitos (las citas cruzadas
máximas son SPEC-02↔SPEC-04 por el artefacto y SPEC-02↔SPEC-03 por C-01,
ambas minoritarias). No se fusiona ni se divide ninguna.

---

## PARTE 2 — Descripciones listas para `/speckit.specify`

### SPEC-01 — Datos meteorológicos en tiempo real

```text
Spec de ingeniería inversa: documenta el comportamiento EXISTENTE de la
resolución de ubicación y la obtención de datos meteorológicos en tiempo
real. No es una feature nueva: es la especificación formal de lo que el
sistema YA hace, para que sirva de contrato en la modernización.

Reglas de la spec:
- Cada requisito y criterio describe el comportamiento ACTUAL con su
  evidencia (fichero y función, o dato real).
- Las anomalías NO se corrigen ni se omiten: se especifican tal cual
  funcionan hoy, referenciadas por su ID del registro de anomalías.
- Los criterios de aceptación deben ser verificables contra la suite de
  tests/, citando el test cuando exista.
- Toda decisión de negocio se cita por su acta (documento, pregunta,
  persona, fecha); las decisiones del acta son SIMULADAS y requieren
  ratificación real.

Alcance (valores concretos):
- Geocodificación: primer resultado del servicio con count=1 y
  language=en (RN-01; open_meteo_adapter.py:64-81). Ejemplo canónico:
  petición "Múnich" → name=Múnich, count=1, language=en; se usa
  results[0].
- Ciudad desconocida: results vacío → NotFoundError → HTTP 404 (RN-02;
  open_meteo_adapter.py:72-74, chat.py:67-72, predict.py:90-94).
- Magnitud ausente: se sustituye por 0 (temperatura, humedad, viento,
  nubes, lluvia) o 1013 hPa (presión) y se sigue adelante (RN-03;
  open_meteo_adapter.py:115-122). Decisión a ratificar: acta P4 no la
  cubre; pregunta pendiente de ratificación real.
- Límites físicos, fronteras inclusivas (RN-04;
  weather/value_objects/__init__.py): temperatura [-100, 100] °C;
  humedad [0, 100] %; presión [870, 1084] hPa; precipitación ≥ 0 mm;
  viento ≥ 0 km/h; nubes [0, 100] %; latitud [-90, 90]; longitud
  [-180, 180]. Ejemplos canónicos: Temperature(-100.0) válida,
  Temperature(-100.1) rompe; Pressure(870) y Pressure(1084) pasan;
  Precipitation(0) pasa. Verificación: tests/test_rn04_value_objects.py
  (fronteras completas con los tres puntos por lado).
- Formatos de texto de los value objects (__str__): "18.5°C", "62.0%",
  "1013.0 hPa", "0.0 mm", "12.3 km/h", "40.0%", "Madrid (40.4168,
  -3.7038)".

Fuera de alcance (otras specs): la extracción de ciudad del texto del
usuario (SPEC-03, RN-22); la conversión de condiciones a características
del modelo (SPEC-02, RN-07/C-01); la ingesta del histórico (SPEC-04);
la capa HTTP común y errores (SPEC-05).
```

### SPEC-02 — Contrato de predicción numérica (`/predict` y modelo en runtime)

```text
Spec de ingeniería inversa: documenta el comportamiento EXISTENTE del
contrato de predicción numérica (endpoint /predict y modelo en runtime).
No es una feature nueva: es la especificación formal de lo que el
sistema YA hace, para que sirva de contrato en la modernización.

Reglas de la spec: (idénticas a SPEC-01: evidencia, anomalías tal cual,
verificabilidad contra tests/, citas de acta simulada).

Alcance (valores concretos):
- Horizontes oficiales de negocio: 6/12/24 h (acta P5); el modelo
  entrenó además 48/72/168, no expuestos (RN-11; predict.py:32-35,
  command.py:19, ask_agent/handler.py:160,165; artefacto: horizons
  [6,12,24,48,72,168]).
- Horizontes no entrenados: se descartan sin aviso; si no queda ninguno,
  ValueError("Prediction result must contain at least one prediction")
  → HTTP 400 con ese texto interno (RN-05/A-07;
  local_predictor.py:215-229, ml/value_objects/__init__.py:126).
  Ejemplo canónico: {"horizons": [6, 999]} → solo se devuelve 6.
- Nombres de salida: {variable}_target_{horizonte}, parseo con
  rsplit("_target_", 1) (RN-06; train_model.py:125-131,
  local_predictor.py:215-229). Ejemplo: temperature_2m_target_24 →
  predictions[24]["temperature_2m"].
- Alineación de entradas: columnas ausentes → 0.0, extra → descartadas,
  city recibe el nombre tal cual ("São Paulo" viaja con acento) (RN-07;
  local_predictor.py:186-192).
- Semántica de lags en runtime: TODOS los lags valen el tiempo actual
  (RN-08/A-04; feature_extractor.py:62-77). Ejemplo canónico:
  temperature_2m_lag_6/_12/_24 reciben las mismas 18,5 °C. Tratamiento
  acordado: aproximación provisional; alinear con la semántica de
  SPEC-04 antes del reentrenamiento (acta P2).
- Viento y rocío a 0 en inferencia (RN-09/A-38): el extractor pide 8
  variables, _weather_to_conditions aporta 6; el modelo además ni las
  consume (44 feature_columns sin dew_point/wind_direction).
- Ciudades fuera del OneHot (A-02/A-20): el codificador solo conoce
  ['Berlin','Cairo','London','Madrid','Mexico City','Mumbai','New
  York','Sydney']; Tokyo/São Paulo/cualquier otra se codifican a ceros
  (handle_unknown="ignore"). Política ratificada (acta P8, §8): solo
  las ciudades entrenadas están soportadas oficialmente. Ejemplo
  canónico (ejecución real 2026-11-14, TS_FIJO, condiciones std):
  Madrid h=6 humidity=60.13257982269474; Tokyo h=6
  humidity=60.92908951903441 (difiere solo ahí).
- La predicción de un horizonte depende de los horizontes pedidos
  (A-43): [6] → 4.250787940828976 °C a 6 h; [6,12,24] →
  18.178030264044768 °C a 6 h (mismas condiciones). Congelado tal cual.
- Sin redondeos en ninguna salida (RN-13/A-39; decisión acta §8): el
  negocio ve todos los decimales (18.5343994140625 saldría tal cual).
- Identidad del modelo servido: md5 truncado + mtime (RN-12/A-22;
  versión actual b59e0918; decisión acta P10: provisional).
- Ruta del modelo: tres valores conviven (A-06/C-05): predictor
  "models/model.pkl", handlers "model.pkl", settings "models/model.pkl".
- Restricción de comunicación (R21, acta P1): prohibido presentar el
  test_score 0.3713 como fiabilidad del producto (es R² entre ciudades:
  test = solo São Paulo + Tokyo).

Fuera de alcance: geocodificación y magnitudes (SPEC-01); la redacción
conversacional y el uso que el chat hace de estas predicciones (SPEC-03,
incluida su ruta de características a ceros A-03); el entrenamiento y
regeneración del artefacto (SPEC-04); configuración, errores HTTP y
persistencia transversales (SPEC-05).

Criterios de aceptación (verificables): tests/test_rn05_rn06_rn07_predictor.py,
tests/test_rn07_rn08_rn09_feature_extractor.py y el golden master
tests/golden_master/master.json (12 casos, cubre por completo esta spec),
regenerable solo con decisión de negocio documentada
(tests/golden_master/LEEME.md).
```

### SPEC-03 — Agente conversacional (`/chat`)

```text
Spec de ingeniería inversa: documenta el comportamiento EXISTENTE del
agente conversacional (POST /chat: intención, extracción de ciudad,
contexto meteorológico/ML/RAG, prompt y LLM). No es una feature nueva:
es la especificación formal de lo que el sistema YA hace, para que sirva
de contrato en la modernización.

Reglas de la spec: (idénticas a SPEC-01).

Alcance (valores concretos):
- Intención por subcadenas con prioridad fija ahora > consejo >
  histórico > pronóstico > general (RN-19/A-12; query_intent.py:165-176).
  Ejemplos canónicos: "I want to know the weather" → CURRENT_CONDITIONS
  ("now" dentro de "know"); "Will it rain in social media" → HISTORICAL
  ("media"); "Should I bring an umbrella right now?" →
  CURRENT_CONDITIONS; "What's the weather?" → GENERAL; "" → ValueError
  ("raw_query must not be empty").
- Ciudad solo con patrones in/at/for/en + NombreCapitalizado, gana el
  primer patrón (RN-22; handler.py:83-93). Ejemplos: "Rain in Spain and
  fog en Paris" → "Spain"; "¿Qué tiempo hará en madrid?" → None.
  CONGELADO (A-42): "Pronóstico for São Paulo" → None y "¿Qué tiempo
  hará en A Coruña?" → None (ñ/ã fuera de la clase de caracteres).
- Pregunta general: sin tiempo ni modelo, con RAG+LLM (RN-20);
  histórica: se responde como tiempo actual (RN-21; decisión acta P12:
  aceptado de momento, histórico en deseos).
- El chat entrega al modelo condiciones actuales nulas (RN-10/A-03;
  C-01): CurrentWeather.to_features() produce claves "temperature",
  "humidity"... que el extractor no reconoce (espera "temperature_2m"...)
  → todos los lags a 0.0. Ejemplo canónico (ejecución real, TS_FIJO):
  mismas condiciones 18,5 °C → /predict 18.178030264044768 °C a 6 h vs
  chat 5.962243504387119 °C a 6 h.
- RAG: toda pregunta recupera top_k=3 por similitud coseno, sin umbral
  (RN-23/A-31; handler.py:118-121,192; decisión acta P13: umbral
  deseado en modernización, hoy aceptado a sabiendas).
- Sesión: una pregunta y una respuesta (RN-24; mensajes exactos
  "Response has already been generated", "Cannot add context after
  response is generated", "query_text must not be empty").
- Prompt al LLM: system prompt fijo en inglés (literal en
  handler.py:36-41) + secciones "### {chunk_type} (source: {source})"
  en orden de inserción + "## User Query" + pregunta (RN-25).
- LLM: sesión compartida por proceso (un UUID por instancia, cabecera
  x-opencode-session), temperatura 0.7, max_tokens 1024, modelo
  mimo-v2.6-flash (RN-26/A-19; contrato aportado en acta §8; incidente
  histórico H3/W3: 400 MissingSessionID).
- Eventos: QueryReceived + ResponseGenerated que se recogen y se
  pierden; used_ml_prediction siempre False porque el agregado busca
  "ml_prediction" y el handler etiqueta "weather_and_prediction"
  (RN-27/A-18).
- Similitud sin acotar (A-33): 1 - (embedding <=> ...) puede salir de
  [0,1] y el value object lo rechaza a mitad de petición (400).
- Contrato HTTP de /chat: NotFoundError→404 con str(exc), ValueError→
  400 con str(exc), excepción cualquiera→500 con detail=str(exc)
  (C-04/A-28; chat.py:63-84).

Fuera de alcance: la resolución de la ciudad contra Open-Meteo y las
magnitudes (SPEC-01); el contrato numérico de la predicción que consume
(SPEC-02); entrenamiento y artefacto (SPEC-04); configuración,
persistencia RAG a nivel de BD, logs y despliegue (SPEC-05, que congelará
C-08/C-09/C-10 y A-32).

Criterios de aceptación (verificables): tests/test_rn19_query_intent.py,
tests/test_rn22_city_extraction.py, tests/test_rn24_rn27_chat_session.py,
tests/test_rn25_rn13_prompt_summary.py, tests/test_c01_conversion_duplicada.py,
tests/test_c03_validacion_vacia.py, tests/test_c04_errores_http.py
(caminos /chat). La búsqueda vectorial real queda fuera de la red.
```

### SPEC-04 — Entrenamiento y ciclo de vida del artefacto ML (offline)

```text
Spec de ingeniería inversa: documenta el comportamiento EXISTENTE del
entrenamiento y el ciclo de vida del artefacto models/model.pkl
(dataset, semántica de lags/targets, partición, constantes, identidad y
reglas protegidas de regeneración). No es una feature nueva: es la
especificación formal de lo que el sistema YA hace, para que sirva de
contrato en la modernización.

Reglas de la spec: (idénticas a SPEC-01).

Alcance (valores concretos):
- Dataset: data/historical_weather.csv, 263.040 filas = 10 ciudades ×
  26.304 horas (2023-01-01 a 2025-12-31), orden por bloques de ciudad,
  UTC verificado por fingerprint horario (arqueología 2026-11-14).
  Alineación de mercado decidida (acta §8): el próximo reentrenamiento
  refresca el histórico priorizando ciudades españolas (Madrid
  referencia), mantiene cobertura global y español prioritario (A-41).
- Partición: int(len × 0.8) truncado, sin shuffle, en el orden del
  fichero (RN-14; train_model.py:166,169-171). COMPORTAMIENTO CRÍTICO
  CONGELADO (A-01): el corte cae al final del bloque de Sydney → el
  test son solo São Paulo + Tokyo; test_score 0.3712878051017324 es R²
  ENTRE CIUDADES. Tratamiento: reentrenar en modernización con split
  correcto (acta P1); prohibido citar 0,37 como fiabilidad (R21).
- Semántica de lags (convención declarada vigente de C-02, RN-15): el
  lag h es el valor de h FILAS antes dentro de la ciudad
  (train_model.py:100, groupby("city").shift(h)); equivalente a h horas
  solo si el CSV es continuo (verificado: 0 huecos, 0 duplicados).
- Targets (RN-16): valor de la variable h filas después
  (shift(-h)); las h últimas filas por ciudad se descartan (dropna).
- Constantes (RN-17): n_estimators=200, max_depth=5, learning_rate=0.1,
  subsample=0.8, random_state=42; horizontes [6,12,24,48,72,168].
- Esquema del artefacto (congelado por tests y golden master): 44
  feature_columns (7 temporales + 6 variables × 6 horizontes + city),
  36 target_columns, OneHot de 8 ciudades
  ['Berlin','Cairo','London','Madrid','Mexico City','Mumbai','New
  York','Sydney'], scores train 0.5431063937097727 / test
  0.3712878051017324.
- Regla protegida con incidente (H4/W1/W2, A-21): la clase
  MultiOutputRegressorWithProgress vive picklada como __main__ dentro
  de model.pkl; moverla inutiliza el activo; el predictor reescribe
  sys.modules["__main__"]. Propietario nominal: Marta Ruiz, equipo de
  datos/ML (acta §8, simulada); cambio del wrapper = reentrenamiento
  coordinado.
- Identidad del artefacto (RN-12/A-22): versión = md5 truncado del
  binario (actual b59e0918), fecha = mtime (acta P10: provisional;
  versión real dentro del fichero en modernización).
- Tablas forecasts/models (A-24, acta P11): forecasts = requisito
  pendiente (histórico consultable de predicciones); models =
  descartada (métricas viajan en el artefacto).
- R² de variable constante se publica como 0 (RN-18/A-40;
  train_model.py:227-228).

Fuera de alcance: el consumo del artefacto en runtime (SPEC-02); la
obtención del histórico desde Open-Meteo archive (SPEC-01 por el
servicio; la descarga del dataset vive aquí como proceso offline);
cualquier capa HTTP (SPEC-05).

Criterios de aceptación (verificables): tests/test_c02_entrenamiento_lags.py
(semántica shift/targets/colas), TestMetadatosDelModeloReal en
tests/test_rn05_rn06_rn07_predictor.py, model_version congelado en
tests/golden_master/master.json. El reentrenamiento completo queda fuera
de la red (solo funciones puras congeladas).
```

### SPEC-05 — Plataforma y operación (transversal)

```text
Spec de ingeniería inversa: documenta el comportamiento EXISTENTE de la
plataforma: configuración y constantes, contratos de error HTTP comunes,
persistencia, credenciales, dependencias, runtime, logs e higiene del
repositorio. No es una feature nueva: es la especificación formal de lo
que el sistema YA hace, para que sirva de contrato en la modernización.

Reglas de la spec: (idénticas a SPEC-01).

Alcance (valores concretos):
- Configuración: Settings de pydantic-settings con .env; valores por
  defecto actuales: database_url
  postgresql+asyncpg://weather:weather@localhost:5432/weather_agent,
  llm_api_url https://opencode.ai/zen/go/v1, llm_model mimo-v2.6-flash,
  open_meteo_base_url https://api.open-meteo.com, model_path
  models/model.pkl, embedder_model all-MiniLM-L6-v2, debug False.
  Credenciales weather/weather SOLO locales (acta P6); prohibido
  producción sin override (checklist de despliegue, H13).
- Contrato de errores HTTP (C-03/C-04/A-27/A-28): entrada vacía ""
  → 422 (Pydantic min_length=1); "   " pasa Pydantic y muere en el
  comando → 400 "query_text must not be empty" (C-03, congelado);
  NotFoundError → 404 detail=str(exc) en AMBAS rutas; ValueError → 400
  detail=str(exc) en ambas; excepción no prevista → /chat 500 con
  detail=str(exc) (expone el texto interno) vs /predict 500 plano
  "Internal Server Error" sin JSON (C-04, asimetría congelada).
- Constantes de contrato (C-10/C-06/C-05): ruta del modelo en tres
  valores ("models/model.pkl" predictor y settings; "model.pkl" en los
  dos handlers); horizontes [6,12,24] repetidos en 5 sitios del
  servicio y [6,12,24,48,72,168] en el artefacto (la lista oficial es
  6/12/24, acta P5); modelo de embeddings "all-MiniLM-L6-v2" en
  settings y adaptador (settings sin consumidor); dimensión 384 en ORM
  e init.sql; LLM duplicado en settings y adaptador. Convención
  declarada (acta P18): settings es el único sitio; defaults a
  unificar en modernización.
- Persistencia: Alembic es la fuente de verdad del esquema (acta P7);
  init.sql solo primer arranque; db-sync deprecado (A-17). Dos fábricas
  de sesión conviven (C-08/A-15). Tablas: knowledge_base (vector(384),
  índice ivfflat) es la única usada en runtime; forecasts/models sin
  escritor (A-24 → SPEC-04).
- Seguridad: sin autenticación, servicio interno en red de confianza
  (acta P4: aceptado); el 500 de /chat expone texto de excepciones:
  NO aceptado, a corregir en modernización (A-05). SQL con
  interpolación de nombre de tabla, patrón latente (A-34).
- Logs: prompt completo del usuario a INFO, SQL completas con
  DEBUG=true; logs internos de uso operativo; texto completo a DEBUG en
  modernización (A-32, acta P14).
- Dependencias y runtime (A-36, acta P15): Python 3.8.10 EOL;
  migración aprobada en modernización; auditoría de CVEs trimestral
  por el equipo de desarrollo; joblib/tqdm/asyncpg/alembic usados y no
  declarados (A-11); pytest 7.4 vs 8.3 resuelto con la suite actual
  (A-37, ya congelada en tests/).
- Higiene (A-23/A-25/A-26): código de dominio sin consumidor
  (Forecast, WeatherInterpretationService, LocationQuery, MockLLM,
  NullLogger, getters de puerto), migración fantasma
  320b6a04018d_test_migration en caché, __pycache__ commiteados,
  docstrings que prometen adaptadores inexistentes. Se inventarían tal
  cual; limpieza en modernización.
- Carrera de carga del modelo (A-35): peticiones concurrentes pueden
  duplicar load_model; cada handler mantiene su copia. Congelado tal
  cual.

Fuera de alcance: todo el comportamiento de negocio de los dominios
(SPEC-01 a SPEC-04); las decisiones de producto (horizontes, ciudades,
redondeo) que solo se referencian aquí como constantes congeladas.

Criterios de aceptación (verificables): tests/test_c03_validacion_vacia.py,
tests/test_c04_errores_http.py, tests/test_c05_c06_c10_constantes.py.
La persistencia real (C-08/C-09, A-10/A-14/A-15/A-16) queda fuera de la
red (requiere PostgreSQL).
```

---

## Tabla resumen

| Spec | Reglas | Anomalías | Dueño (acta) | Tests |
|---|---|---|---|---|
| SPEC-01 Datos meteorológicos en tiempo real | RN-01, RN-02, RN-03, RN-04 | — (RN-03 DUDOSA a ratificar) | producto (P8) + TI (RN-03) | test_rn04_value_objects; IO fuera de red |
| SPEC-02 Contrato de predicción numérica | RN-05, RN-06, RN-07, RN-08, RN-09, RN-11, RN-13 | A-02, A-04, A-06, A-07, A-08, A-20, A-38, A-39, A-43 | producto de predicción (P1, P2, P5, P16) | test_rn05_rn06_rn07_predictor, test_rn07_rn08_rn09_feature_extractor; **golden master completo** |
| SPEC-03 Agente conversacional | RN-10, RN-19, RN-20, RN-21, RN-22, RN-23, RN-24, RN-25, RN-26, RN-27 | A-03, A-12, A-18, A-19, A-29, A-30, A-31, A-33, A-42 | producto (P5, P8, P12, P13) + compras (P3/§8) | test_rn19_query_intent, test_rn22_city_extraction, test_rn24_rn27_chat_session, test_rn25_rn13_prompt_summary, test_c01 (chat), test_c03, test_c04 (/chat) |
| SPEC-04 Entrenamiento y artefacto ML | RN-12, RN-14, RN-15, RN-16, RN-17, RN-18 | A-01, A-21, A-22, A-24, A-40, A-41 | datos/ML (P9, §8) | test_c02_entrenamiento_lags, metadatos del artefacto, model_version en master |
| SPEC-05 Plataforma y operación | — (contratos transversales: C-03, C-04, C-05, C-06, C-08, C-09, C-10) | A-05, A-09, A-10, A-11, A-13, A-14, A-15, A-16, A-17, A-23, A-25, A-26, A-27, A-28, A-32, A-34, A-35, A-36, A-37 | TI/infraestructura (P4, P6, P7, P14, P15) | test_c03, test_c04, test_c05_c06_c10 |

**Cobertura**: 27 de 28 reglas asignadas (RN-28 excluida: refutada por
arqueología); 43 de 43 anomalías asignadas. Exclusiones justificadas:
riesgos R1-R21 (viajan con su anomalía), memoria histórica (evidencia),
código muerto (inventario en SPEC-05).

**Pendiente antes de ejecutar** (`/speckit.specify`): aprobación de esta
partición y ratificación real del acta simulada (rondas 1 y 2).
