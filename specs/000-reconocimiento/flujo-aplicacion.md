# Flujo de aplicación — ciclo de vida de una pregunta sobre el clima

Documento de caracterización de la fase de reconocimiento. Describe el camino
completo que recorre una pregunta del usuario por el código, tal como es hoy,
sin corregir nada (constitución, Principio I y III). Toda afirmación lleva
evidencia `fichero:línea` (Principio II).

Ámbito: la única entrada conversacional del sistema es `POST /chat`
(`src/infrastructure/http/routes/chat.py:47-53`). La predicción numérica
(`POST /predict`, `routes/predict.py:69-75`) se documenta como caso aparte en
§5 porque comparte subflujo. La UI web (`GET /`) solo sirve el HTML que llama
a `/chat` (`src/main.py:44-48`, `chat.html:357-358`).

---

## 1. Entrada: del navegador a la ruta

1. El usuario escribe en la página servida por `GET /`
   (`main.py:44-48`, que cachea `infrastructure/http/static/chat.html`,
   `main.py:35-42`).
2. El JavaScript de la página hace `fetch('/chat', { method: 'POST', ... })`
   (`chat.html:357-358`).
3. FastAPI valida el cuerpo contra `ChatRequest`, que exige `query` con
   `min_length=1` (`chat.py:27`).

**Caso A — cuerpo inválido (query ausente o `""`):** la validación es de
Pydantic y falla antes de tocar el código de aplicación; FastAPI responde
**422** (comportamiento por defecto de FastAPI ante `RequestValidationError`;
evidencia: `chat.py:27` no define manejador propio y `chat.py:63-84` nunca
llega a ejecutarse).

**Caso B — `query="   "` (solo espacios):** pasa la validación de Pydantic
(`min_length=1` lo admite, `chat.py:27`) pero falla la validación de dominio
en `AskAgentCommand.__post_init__` (`application/ask_agent/command.py:19-21`)
→ `ValueError` → manejador de `chat.py:73-78` → **400**.

> Nota: A y B son "lo mismo" para el negocio (entrada vacía) con dos capas de
> validación distintas y códigos HTTP distintos (422 vs 400). Ver §6.d.

## 2. Arranque del caso de uso (`AskAgentHandler.execute`)

La ruta resuelve el caso de uso del contenedor DI
(`chat.py:42-44`; cableado en `infrastructure/config/di.py:80-90`) y llama a
`execute(command)` (`chat.py:64-65`).

### Paso 1 — Sesión e intención (`handler.py:104-108`)

- Se crea `ChatSession(query_text=...)`, que valida texto no vacío y registra
  el evento `QueryReceived` (`domain/agent/aggregate/__init__.py:47-57`).
- Se clasifica la intención con `QueryIntent.from_query` por palabras clave
  (`handler.py:107`; clasificador en `domain/agent/value_objects/query_intent.py:151-179`).

**Casos de intención** (orden de evaluación real, `query_intent.py:165-176`:
primero "current", luego "advice", luego "historical", y "forecast" como
comodín):

| Intención | Palabras clave que la disparan (ejemplos) | Evidencia |
|---|---|---|
| CURRENT_CONDITIONS | "ahora", "hoy", "actual", "now", "today" | `query_intent.py:79-92` |
| ADVICE | "debería", "paraguas", "abrigo", "should i", "umbrella" | `query_intent.py:55-77` |
| HISTORICAL | "ayer", "histórico", "promedio", "año pasado", "average" | `query_intent.py:94-110` |
| FORECAST | "lloverá", "mañana", "pronóstico", "temperatura", "rain", "tomorrow" | `query_intent.py:19-53` |
| GENERAL | ninguna coincidencia | `query_intent.py:175-176` |

Solo las cuatro primeras son "meteorológicas"
(`is_weather_related`, `query_intent.py:141-147`).

**Caso C — intención GENERAL** (p. ej. "¿quién eres?"): no se consulta el
tiempo ni el modelo. El flujo salta directamente al RAG y al LLM
(`handler.py:111-120`: el bloque del tiempo queda dentro de
`if intent.is_weather_related`). La respuesta se genera solo con documentos
meteorológicos + la pregunta.

**Caso D — intención HISTORICAL** (p. ej. "¿llovió más el año pasado en
Madrid?"): es meteorológica, pero **no existe camino a datos históricos en
runtime**: el handler solo llama a `geocode` + `get_current_weather`
(`handler.py:151-152`); el método `get_historical_weather`
(`open_meteo_adapter.py:125-171`) no tiene llamador en la API. Una pregunta
histórica se responde como si fuera de tiempo actual.

### Paso 2 — Contexto meteorológico (solo si hay intención y ciudad)

`_extract_city` busca patrones "in/at/for/en + Nombre Capitalizado"
(`handler.py:83-93`).

**Caso E — pregunta meteorológica sin ciudad detectable** (p. ej. "¿lloverá
mañana?"): `_extract_city` devuelve `None` (`handler.py:89-93`), el bloque
`if city:` no se ejecuta (`handler.py:114`) y no hay contexto de tiempo ni
predicción. Flujo equivalente al caso C pero con intención meteorológica.

**Caso F — pregunta meteorológica con ciudad** (p. ej. "¿lloverá mañana en
Madrid?"): subflujo `_gather_weather_context` (`handler.py:143-182`), en este
orden:

1. **Geocodificación**: `OpenMeteoAdapter.geocode` contra
   `geocoding-api.open-meteo.com/v1/search` (`open_meteo_adapter.py:64-68`).
   - **F1 — ciudad inexistente**: `results` vacío → `NotFoundError`
     (`open_meteo_adapter.py:72-74`) → manejador de la ruta → **404**
     (`chat.py:67-72`).
2. **Tiempo actual**: `get_current_weather` contra
   `api.open-meteo.com/v1/forecast` (`open_meteo_adapter.py:98-109`).
   - **F2 — respuesta sin bloque `current`** → `NotFoundError` → **404**
     (`open_meteo_adapter.py:111-113`).
   - **F3 — error HTTP de Open-Meteo** → `raise_for_status`
     (`open_meteo_adapter.py:108`) → excepción httpx no contemplada en la
     ruta → **500** (`chat.py:79-84`).
3. **Carga perezosa del modelo**: `LocalPredictor.load_model`
   (`local_predictor.py:49-86`, invocado desde `handler.py:64-68`).
   - **F4 — `models/model.pkl` no existe** → `FileNotFoundError`
     (`local_predictor.py:63-64`). La ruta NO lo traduce: cae en el
     manejador genérico → **500** (`chat.py:79-84`). Evidencia adicional: la
     ruta solo mapea `NotFoundError`, `ValueError` y `Exception`
     (`chat.py:67-84`).
4. **Extracción de características**: `TemporalFeatureExtractor.extract`
   (`feature_extractor.py:24-82`) recibe `current_weather.to_features()`
   (`handler.py:157`). **Anomalía ya registrada** en el mapa del sistema
   (§4.1): `to_features()` produce claves `"temperature"`, `"humidity"`…
   (`weather/repository/__init__.py:57-62`) que no coinciden con las que
   espera el extractor (`"temperature_2m"`, … `feature_extractor.py:63-72`),
   por lo que todos los lags valen 0.0 (`feature_extractor.py:76`,
   `local_predictor.py:191`). Se documenta, no se corrige.
5. **Predicción**: `LocalPredictor.predict` → `pipeline.predict` sobre un
   DataFrame alineado (`local_predictor.py:88-128`).
6. **Contexto añadido a la sesión** como chunk
   `chunk_type="weather_and_prediction"` (`handler.py:171-182`).

### Paso 3 — RAG (siempre, sea cual sea la intención)

`_gather_rag_context` se ejecuta para TODA pregunta, meteorológica o no
(`handler.py:118-121`; comentario del propio código: "always").

1. **Embedding de la pregunta**: `LocalEmbedder.embed` con el modelo local
   `all-MiniLM-L6-v2` (descarga perezosa en el primer uso;
   `local_embedder.py:22,26-30`).
2. **Búsqueda vectorial**: `KnowledgeBaseAdapter.search` con SQL crudo contra
   pgvector, `top_k=3` (`knowledge_base_adapter.py:69-82`).
   - **Caso G — sin documentos**: se registra en el log y se continúa sin
     contexto RAG (`handler.py:204-205`).
   - **Caso H — PostgreSQL caído o tabla ausente**: excepción de SQLAlchemy
     no contemplada → **500** (`chat.py:79-84`). La tabla se crea en
     `init.sql:16-23` y el índice en la migración
     `alembic/versions/821f93690b12_...py:20-24`.
3. Los documentos se convierten en chunks `chunk_type="rag_document"`
   (`agent/aggregate/__init__.py:74-91`, invocado desde `handler.py:203`).

### Paso 4 — Prompt y LLM

1. `_build_prompt` compone: system prompt + contextos + pregunta
   (`handler.py:207-235`; system prompt en `handler.py:36-41`).
2. `OpenCodeGoLLM.generate` envía el prompt a
   `https://opencode.ai/zen/go/v1/chat/completions` con el modelo
   `mimo-v2.6-flash` y cabecera obligatoria `x-opencode-session`
   (`opencode_go_llm.py:34-44,59-77`).
   - **Caso I — API key vacía** (valor por defecto `""` en `settings.py:10`
     si no hay `.env`): la petición sale sin credencial válida → error HTTP →
     `raise_for_status` (`opencode_go_llm.py:81`) → **500**.
   - **Caso J — error/timeout del LLM** (timeout 30 s, `opencode_go_llm.py:36`)
     → excepción httpx → **500** (`chat.py:79-84`).

### Paso 5 — Respuesta y cierre

1. `session.generate_response(response)` valida que no haya respuesta previa
   y registra `ResponseGenerated` (`agent/aggregate/__init__.py:95-114`).
2. `pop_events()` devuelve los eventos y **se descartan** (no se persisten ni
   publican; `handler.py:134-141`). Anomalía ya registrada (mapa del sistema
   §4.9): `used_ml_prediction` siempre `False` porque el handler etiqueta el
   chunk como `"weather_and_prediction"` y el agregado busca
   `"ml_prediction"` (`aggregate/__init__.py:106` vs `handler.py:173`).
3. La ruta empaqueta `response` y `session_id` en `ChatResponse`
   (`chat.py:86-89`).

---

## 3. Matriz de casos

| Caso | Entrada | Camino recorrido | Resultado HTTP |
|---|---|---|---|
| A | cuerpo sin `query` o `""` | Pydantic (`chat.py:27`) | 422 |
| B | `query="   "` | Pydantic → `AskAgentCommand` (`command.py:19-21`) | 400 |
| C | intención GENERAL ("¿quién eres?") | handler pasos 1, 3, 4, 5 (`handler.py:111-141`) | 200 (si RAG y LLM funcionan) |
| D | intención HISTORICAL | igual que FORECAST (no hay camino histórico en runtime, `handler.py:151-152`) | 200 |
| E | meteorológica sin ciudad | handler pasos 1, 3, 4, 5 (sin paso 2, `handler.py:114`) | 200 |
| F1 | ciudad no geolocalizable | paso 2.1 (`open_meteo_adapter.py:72-74`) | 404 |
| F2 | Open-Meteo sin `current` | paso 2.2 (`open_meteo_adapter.py:111-113`) | 404 |
| F3 | error HTTP de Open-Meteo | paso 2.2 (`open_meteo_adapter.py:108`) | 500 |
| F4 | `models/model.pkl` ausente | paso 2.3 (`local_predictor.py:63-64`) | 500 |
| G | RAG sin resultados | paso 3 (`handler.py:204-205`) | 200 |
| H | PostgreSQL caído | paso 3.2 (`knowledge_base_adapter.py:80-82`) | 500 |
| I | `LLM_API_KEY` sin configurar | paso 4 (`settings.py:10`, `opencode_go_llm.py:81`) | 500 |
| J | error/timeout del LLM | paso 4 (`opencode_go_llm.py:36,81`) | 500 |

Cualquier otro error no contemplado cae en el manejador genérico
(`chat.py:79-84`, **500** con el texto de la excepción en `detail`).

---

## 4. Caso aparte: `POST /predict` (subflujo compartido)

`PredictHandler.execute` (`application/predict/handler.py:50-94`) recorre:
geocodificar (`:62`) → tiempo actual (`:65`) → cargar modelo (`:68`) →
extraer características (`:71-77`) → predecir (`:80-84`). Difiere del chat en:

- Usa `self._weather_to_conditions` con claves correctas de Open-Meteo
  (`predict/handler.py:108-115`), no `to_features()`.
- No pasa por RAG ni LLM.
- La ruta duplica el mismo mapeo de errores que `/chat`
  (`routes/predict.py:90-99` vs `routes/chat.py:67-84`).

---

## 5. Anomalías del flujo ya registradas (referencia)

- Características a 0 en el chat: mapa del sistema §4.1 (evidencia en §2,
  paso 2.4 de este documento).
- `used_ml_prediction` siempre `False`: mapa del sistema §4.2
  (`aggregate/__init__.py:106` vs `handler.py:173`).
- Eventos de sesión descartados: mapa del sistema §4.9 (`handler.py:134-135`).
- RAG ejecutado siempre, incluso para intención GENERAL: §2, paso 3 de este
  documento (`handler.py:118-121`).

---

## 6. Puntos donde dos caminos hacen "lo mismo" con código distinto

Registrados como hallazgos, sin corregir (Principio III).

**a. Convertir el tiempo actual en características del modelo — dos
implementaciones con claves incompatibles.**
`CurrentWeather.to_features()` (`weather/repository/__init__.py:50-63`,
claves `"temperature"`, `"humidity"`, …) y
`PredictHandler._weather_to_conditions` (`predict/handler.py:96-115`, claves
`"temperature_2m"`, `"relative_humidity_2m"`, …) hacen lo mismo (tiempo
actual → diccionario de características) con código distinto y resultado
distinto. El chat usa la primera (`handler.py:157`) y el predict la segunda
(`predict/handler.py:71`). Consecuencia: la anomalía §4.1 del mapa.

**b. Ingeniería de características duplicada entre runtime y entrenamiento.**
`TemporalFeatureExtractor.extract` (`feature_extractor.py:47-77`) reproduce a
mano la lógica de `engineer_features` del entrenamiento
(`scripts/train_model.py:78-101`): mismos nombres (`hour_sin`, `month_cos`,
lags `{var}_lag_{h}`), dos implementaciones independientes que deben seguir
en sincronía para que `model.pkl` reciba lo que espera
(`feature_extractor.py:21` lo reconoce: "This matches the feature engineering
in scripts/train_model.py").

**c. Mapeo de errores HTTP duplicado entre rutas.** `chat.py:67-84` y
`predict.py:90-99` contienen el mismo bloque try/except (404/400) con código
copiado; el de `chat.py` añade además el `except Exception` genérico y el de
`predict.py` no (un error imprevisto en `/predict` produce la respuesta 500
por defecto de FastAPI, con traceback distinto al de `/chat`).

**d. Validación de entrada vacía en dos capas con códigos distintos.** El
mismo problema de negocio (pregunta vacía) se resuelve con 422 si falla
Pydantic (`chat.py:27`) y con 400 si falla el dominio
(`command.py:19-21` → `chat.py:73-78`). Ver §1, casos A y B.

**e. Generación de embeddings en dos sitios.** El runtime usa el adaptador
`LocalEmbedder` (`local_embedder.py:12-30`); el script de ingesta carga su
propia instancia de `SentenceTransformer` con el mismo modelo
(`scripts/ingest_knowledge.py:29,357`), sin pasar por el adaptador. Mismo
trabajo, dos implementaciones.

**f. Obtención de sesiones de base de datos en dos sitios.**
`KnowledgeBaseAdapter` construye su propia `async_sessionmaker` a partir del
engine (`knowledge_base_adapter.py:34-37`), mientras
`persistence/session.py:29-50` define `get_session_factory`/`get_session`
para el mismo propósito y no tiene llamadores en runtime (mapa del sistema
§4.8).

**g. Interpretación de la misma frase en dos mecanismos distintos.** La
intención se clasifica por listas de palabras clave
(`query_intent.py:150-179`) y la ciudad se extrae por expresiones regulares
independientes (`handler.py:83-93`); ambos analizan la misma frase del
usuario con lógica no compartida: pueden discrepar (p. ej. intención
GENERAL con ciudad detectable, o al revés), y cada uno evoluciona por
separado.

---

## 7. Preguntas abiertas (SUPOSICIÓN → pregunta)

- **SUPOSICIÓN**: el caso D (preguntas históricas respondidas con tiempo
  actual) es un comportamiento actual y no una funcionalidad pendiente.
  *¿Lo confirma el negocio (nombre y fecha)?*
- **SUPOSICIÓN**: el `detail` de los errores 500 devuelve el texto de la
  excepción al cliente (`chat.py:81-84`), incluidos errores internos de
  base de datos o del LLM. *¿Se considera comportamiento aceptable a
  proteger?*
- **SUPOSICIÓN**: en el caso F1, la geocodificación usa `language=en`
  (`open_meteo_adapter.py:65`), con lo que nombres españoles sin mayúscula
  inicial o con artículos no se extraen (`handler.py:83-93`). *¿Es aceptable
  el alcance actual de extracción de ciudades?*
