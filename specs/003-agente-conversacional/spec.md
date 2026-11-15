# Feature Specification: SPEC-03 — Agente conversacional (`/chat`)

**Feature Branch**: `specs/003-agente-conversacional` (sin rama git: hook `before_specify` saltado por decisión del usuario)

**Created**: 2026-11-14

**Status**: Draft

**Input**: Especificación inversa de `propuesta-particion-specs.md` (PARTE 2, SPEC-03). Spec de ingeniería inversa: documenta el comportamiento EXISTENTE del agente conversacional (POST `/chat`: intención, extracción de ciudad, contexto meteorológico/ML/RAG, prompt y LLM). No es una feature nueva: es la especificación formal de lo que el sistema YA hace, para que sirva de contrato en la modernización.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - La intención se decide por subcadenas con prioridad fija (Priority: P1)

La primera lista de palabras que aparezca como subcadena de la pregunta (en minúsculas) decide la intención, en el orden estado actual > consejo > histórico > pronóstico > general (RN-19/A-12; `query_intent.py:165-176`).

**Why this priority**: decide si la pregunta toca el tiempo, el modelo y el RAG: es la puerta del flujo conversacional.

**Independent Test**: `tests/test_rn19_query_intent.py` (casos del documento + fronteras de orden + validación).

**Acceptance Scenarios**:

1. **Given** "I want to know the weather", **When** se clasifica, **Then** → CURRENT_CONDITIONS ("now" dentro de "know").
2. **Given** "Will it rain in social media", **When** se clasifica, **Then** → HISTORICAL ("media" antes que "rain").
3. **Given** "Should I bring an umbrella right now?", **When** se clasifica, **Then** → CURRENT_CONDITIONS (ahora > consejo).
4. **Given** "What's the weather?", **When** se clasifica, **Then** → GENERAL (sin palabra clave: comodín).
5. **Given** "" o "   ", **When** se clasifica, **Then** → `ValueError("raw_query must not be empty")` (no hay intención).

---

### User Story 2 - Ciudad solo con patrones "in/at/for/en + NombreCapitalizado" (Priority: P1)

La ciudad se extrae si va precedida de "in", "at", "for" o "en" (en ese orden, gana el primero) seguida de palabras con inicial mayúscula (RN-22; `handler.py:83-93`). CONGELADO tal cual (A-42): ñ/ã no están en la clase de caracteres.

**Why this priority**: sin ciudad no hay contexto meteorológico en el chat.

**Independent Test**: `tests/test_rn22_city_extraction.py`.

**Acceptance Scenarios**:

1. **Given** "Rain in Spain and fog en Paris", **When** se extrae, **Then** → "Spain" (gana el primer patrón).
2. **Given** "¿Qué tiempo hará en madrid?", **When** se extrae, **Then** → None (minúscula).
3. **Given** "Pronóstico for São Paulo" o "¿Qué tiempo hará en A Coruña?", **When** se extrae, **Then** → None (A-42 congelado; corrección solo en modernización).

---

### User Story 3 - El chat predice con condiciones actuales nulas (comportamiento congelado) (Priority: P1)

El chat entrega al modelo las claves de `CurrentWeather.to_features()` ("temperature", "humidity"…), que el extractor no reconoce (espera "temperature_2m"…): todos los lags entran a 0.0 (RN-10/A-03; C-01). Las predicciones conversacionales parten de un estado meteorológico nulo.

**Why this priority**: es la divergencia de mayor impacto visible del sistema; congelada tal cual, corrección en modernización (acta P16: la convención oficial es la de Open-Meteo).

**Independent Test**: `tests/test_c01_conversion_duplicada.py` (las dos implementaciones por separado) y `TestA03ChatPrediceConCeros` en `tests/test_rn05_rn06_rn07_predictor.py`.

**Acceptance Scenarios**:

1. **Given** las mismas condiciones (18,5 °C, 62 %, 1013 hPa…), **When** se predice por la ruta del chat vs `/predict`, **Then** a 6 h: 5.962243504387119 °C (chat) vs 18.178030264044768 °C (`/predict`).
2. **Given** las dos conversiones, **When** se comparan claves, **Then** solo comparten `cloud_cover` y `precipitation` (4 claves difieren).

---

### User Story 4 - RAG siempre, top-3, sin umbral (Priority: P2)

Toda pregunta (meteorológica o no) recupera hasta 3 documentos por similitud coseno, sin puntuación mínima (RN-23/A-31; `handler.py:118-121,192`). Decisión acta P13: umbral deseado en modernización; hoy aceptado a sabiendas.

**Why this priority**: condiciona el coste y la calidad de cada respuesta.

**Independent Test**: IO (PostgreSQL/pgvector) fuera de la suite; contrato congelado por evidencia de líneas y constante `top_k=3`.

**Acceptance Scenarios**:

1. **Given** "hola" (sin sentido meteorológico), **When** se procesa, **Then** se buscan los 3 documentos más similares y entran al prompt como chunks `rag_document`.

---

### User Story 5 - Sesión, prompt y parámetros de LLM fijos (Priority: P2)

Una conversación es una pregunta y una respuesta (RN-24); el prompt es system prompt fijo en inglés + secciones `### {chunk_type} (source: {source})` en orden de inserción + `## User Query` + pregunta (RN-25; `handler.py:36-41,221-235`); el LLM recibe sesión compartida por proceso (un UUID por instancia, cabecera `x-opencode-session`), temperatura 0.7, max_tokens 1024, modelo mimo-v2.6-flash (RN-26/A-19; contrato aportado en acta §8; incidente histórico H3/W3: 400 MissingSessionID).

**Why this priority**: define el contrato de redacción que el negocio ve en cada respuesta.

**Independent Test**: `tests/test_rn24_rn27_chat_session.py`, `tests/test_rn25_rn13_prompt_summary.py`, `tests/test_c05_c06_c10_constantes.py::test_congela_parametros_llm`.

**Acceptance Scenarios**:

1. **Given** una sesión ya respondida, **When** se intenta responder o añadir contexto, **Then** `ValueError("Response has already been generated")` / `"Cannot add context after response is generated"`.
2. **Given** una sesión sin contexto, **When** se construye el prompt, **Then** es exactamente: system prompt + "\n\n## User Query\n\n" + pregunta.
3. **Given** dos usuarios del mismo proceso, **When** ambos conversan, **Then** comparten la misma cabecera de sesión LLM.

---

### User Story 6 - Preguntas generales e históricas (Priority: P2)

Pregunta general: sin tiempo ni modelo, con RAG+LLM (RN-20). Pregunta histórica: se responde como tiempo actual; el método histórico de la API nunca se llama en runtime (RN-21; acta P12: aceptado de momento, histórico real en deseos).

**Why this priority**: delimita qué preguntas reciben dato real y cuáles no.

**Independent Test**: evidencia de líneas (`query_intent.py:99,141-147`, `handler.py:110-121,151-152`, `open_meteo_adapter.py:125-171` sin llamador); verificación contractual.

**Acceptance Scenarios**:

1. **Given** "¿quién eres?", **When** se procesa, **Then** no se geocodifica ni predice; se buscan documentos y se llama al LLM.
2. **Given** "¿Llovió más el año pasado en Madrid?", **When** se procesa, **Then** intención HISTORICAL → geocode + tiempo actual + modelo (sin datos históricos).

---

### User Story 7 - Los eventos de la conversación se pierden (comportamiento congelado) (Priority: P3)

Cada conversación genera QueryReceived + ResponseGenerated que se recogen y descartan; `used_ml_prediction` es siempre False porque el agregado busca `"ml_prediction"` y el handler etiqueta `"weather_and_prediction"` (RN-27/A-18).

**Why this priority**: bloquea auditoría/analítica futura, pero no afecta al servicio actual.

**Independent Test**: `tests/test_rn24_rn27_chat_session.py::TestRN27EventosQueSePierden`.

**Acceptance Scenarios**:

1. **Given** un chat sobre Madrid con contexto meteorológico y RAG, **When** se responde, **Then** el evento tiene `used_rag=True`, `used_ml_prediction=False` y se pierde tras `pop_events()`.

---

### Edge Cases

- Entrada vacía: "" → 422 (Pydantic `min_length=1`); "   " pasa Pydantic y muere en el comando → 400 (C-03, congelado en `tests/test_c03_validacion_vacia.py`).
- Contrato de errores `/chat`: `NotFoundError`→404 con `detail=str(exc)`; `ValueError`→400 con `detail=str(exc)`; excepción cualquiera→500 con `detail=str(exc)` (expone el texto interno; C-04, congelado).
- Similitud sin acotar (A-33): `1 - (embedding <=> …)` puede salir de [0,1] y el value object lo rechaza a mitad de petición (400).
- Preguntas con acentos/tildes en la ciudad ("Múnich" sí; "São Paulo"/"A Coruña" no, A-42).
- Resumen meteorológico del chat sin redondeo (RN-13; "N/A" para variables ausentes).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE clasificar la intención por subcadenas con el orden fijo ahora > consejo > histórico > pronóstico > general. Evidencia: `query_intent.py:165-176`.
- **FR-002**: El sistema DEBE extraer la ciudad solo con los patrones in/at/for/en + NombreCapitalizado (primer patrón gana) y DEBE fallar con ñ/ã tal cual está congelado (A-42). Evidencia: `handler.py:83-93`.
- **FR-003**: El sistema DEBE consultar el tiempo y el modelo solo para intenciones meteorológicas, y DEBE responder las históricas con tiempo actual (RN-20/RN-21).
- **FR-004**: El sistema DEBE pasar al extractor las claves de `to_features()` tal cual (ruta del chat), con el resultado de lags a 0.0 (A-03 congelado; corrección solo en modernización).
- **FR-005**: El sistema DEBE recuperar top_k=3 documentos RAG sin umbral para toda pregunta (acta P13: umbral en modernización).
- **FR-006**: El sistema DEBE permitir exactamente una respuesta por sesión, con los mensajes de error congelados (RN-24).
- **FR-007**: El sistema DEBE componer el prompt con el orden y formato congelados (RN-25) y DEBE llamar al LLM con sesión compartida por proceso, temperatura 0.7, 1024 tokens (RN-26/A-19, acta §8).
- **FR-008**: El sistema DEBE generar y descartar los eventos QueryReceived/ResponseGenerated con `used_ml_prediction` siempre False (A-18 congelado).
- **FR-009**: El sistema DEBE mantener el contrato de errores de `/chat` tal cual (404/400 con detalle; 500 con texto interno, C-04).

### Key Entities

- **ChatSession**: pregunta → contextos (weather_and_prediction, rag_document) → respuesta; eventos internos desechables.
- **QueryIntent**: tipo + confianza (siempre 1.0 por defecto) + consulta original.
- **RetrievedDocument**: título, contenido, categoría, similitud [0,1].

## Success Criteria *(mandatory)*

- **SC-001**: todos los casos de intención y extracción de ciudad del documento y sus fronteras en verde (`test_rn19_query_intent`, `test_rn22_city_extraction`).
- **SC-002**: la divergencia C-01 congelada con valores reales (chat 5.96 vs /predict 18.18 °C a 6 h) en `test_c01_conversion_duplicada.py` y `TestA03ChatPrediceConCeros`.
- **SC-003**: el prompt del LLM congelado literalmente (`test_rn25_rn13_prompt_summary`).
- **SC-004**: decisiones citadas por acta (P3/§8, P12, P13, P16) marcadas como simuladas pendientes de ratificación.

## Assumptions

- El endpoint OpenCode Go y su contrato (acta §8) no cambian durante la fase de protección.
- La base de conocimiento RAG mantiene sus ~23 documentos y la dimensión 384 (SPEC-005).
- Decisiones de acta simulada pendientes de ratificación real.

## Fuera de alcance

- Resolución de la ciudad contra Open-Meteo y magnitudes → SPEC-001.
- Contrato numérico de la predicción que el chat consume → SPEC-002.
- Entrenamiento y artefacto → SPEC-004.
- Configuración, persistencia RAG a nivel de BD (C-08/C-09/C-10), logs y despliegue → SPEC-005.
