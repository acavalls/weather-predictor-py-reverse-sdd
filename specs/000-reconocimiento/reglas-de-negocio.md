# Reglas de negocio del núcleo — specs/000-reconocimiento

Extracción de las reglas de negocio que implementan los módulos de lógica de
negocio central con criticidad **ALTA** según el mapa del sistema
(`specs/000-reconocimiento/mapa-sistema.md`), junto con sus utilidades:

- `application/predict/handler.py` (ALTA) y `application/ask_agent/handler.py` (ALTA)
- `domain/weather/repository/__init__.py` (ALTA), `domain/ml/repository/__init__.py`
  y `domain/ml/value_objects/__init__.py` (ALTA)
- utilidades del dominio agente: `domain/agent/aggregate/__init__.py` (MEDIA),
  `domain/agent/value_objects/query_intent.py` (MEDIA)
- `infrastructure/weather/open_meteo_adapter.py` (ALTA),
  `infrastructure/ml/local_predictor.py` (ALTA), `feature_extractor.py` (ALTA),
  `model_wrapper.py` (ALTA, utilidad), `llm/opencode_go_llm.py` (ALTA)
- `scripts/train_model.py` (ALTA, utilidad de entrenamiento que genera el
  activo `models/model.pkl`, ALTA)

Reglas escritas como reglas de negocio, no como descripción de código.
Clasificación provisional (Principio II): **INTENCIONAL** (decisión
deliberada con señales), **ACCIDENTAL** (efecto colateral de la
implementación) o **DUDOSA** (indecidible desde el código → pregunta).
Nada se corrige (Principio III). Cada discrepancia comentario/código es un
hallazgo y se marca como tal.

---

## A. Predicción numérica (motor ML y `POST /predict`)

**RN-01 — Geolocalización: primer resultado del servicio, en inglés.**
Enunciado: para resolver una ciudad, el sistema toma el primer resultado que
devuelve el servicio de geocodificación (solo se pide 1) y lo consulta en
inglés.
Ejemplo: petición "Múnich" → el servicio recibe `name=Múnich, count=1,
language=en`; el sistema usa el primer elemento de `results` aunque existan
varias Múnich.
Evidencia: `open_meteo_adapter.py:64-81` (`params` en `:65`, `results[0]` en `:76-81`).
Clasificación: **INTENCIONAL** (`count: 1` explícito).

**RN-02 — Ciudad desconocida: la petición se rechaza.**
Enunciado: si el servicio no reconoce la ciudad, no hay predicción ni
respuesta; el negocio recibe un rechazo de "no encontrado".
Ejemplo: `geocode("Ahoraqueloscilae")` → `results` vacío → `NotFoundError`
→ HTTP 404.
Evidencia: `open_meteo_adapter.py:72-74`; mapeo a 404 en `chat.py:67-72`
y `predict.py:90-94`.
Clasificación: **INTENCIONAL**.

**RN-03 — Si una magnitud no llega, se inventa un valor neutral.**
Enunciado: cuando el proveedor no trae una variable del tiempo actual, el
sistema la sustituye por 0 (temperatura, humedad, viento, nubes, lluvia) o
1013 hPa (presión), y sigue adelante.
Ejemplo: respuesta de Open-Meteo sin `cloud_cover` → el modelo y el resumen
trabajan con "nubes 0,0 %" aunque el cielo esté cubierto.
Evidencia: `open_meteo_adapter.py:115-122` (`.get(..., 0)`, `.get(..., 1013)`).
Clasificación: **DUDOSA** (el código lo hace deliberadamente, pero ¿es una
decisión de negocio o un comodín de implementación? → pregunta).
Hallazgo asociado: el comentario del método promete "CurrentWeather with all
measured variables" (`open_meteo_adapter.py:92-93`); con valores por defecto
no son "variables medidas".

**RN-04 — Límites físicos de las magnitudes (fronteras inclusivas).**
Enunciado: toda magnitud debe caer en su rango físico; los extremos son
válidos (las comparaciones excluyen solo lo que sale del rango):
temperatura [-100, 100] °C; humedad [0, 100] %; presión [870, 1084] hPa;
precipitación ≥ 0 mm; viento ≥ 0 km/h; nubes [0, 100] %; latitud
[-90, 90]; longitud [-180, 180].
Ejemplo: `Temperature(-100.0)` es válida (solo `< -100` falla);
`Temperature(-100.1)` rompe; `Pressure(870)` y `Pressure(1084)` pasan;
`Precipitation(0)` pasa.
Evidencia: `weather/value_objects/__init__.py:20-24` (Location),
`:39-42` (Temperature), `:54-56` (Humidity), `:68-70` (Pressure),
`:82-84` (Precipitation), `:96-98` (WindSpeed), `:110-112` (CloudCover).
Clasificación: **INTENCIONAL** (validaciones explícitas con mensaje).

**RN-05 — Solo se responden horizontes que el modelo conoce.**
Enunciado: de los horizontes pedidos, solo se devuelven los que el modelo
entrenó; el resto se descartan sin aviso y, si no queda ninguno, la petición
falla.
Ejemplo: `POST /predict {"horizons": [6, 999]}` → el modelo solo tiene
columnas `_target_6/12/24/48/72/168`; `999` se filtra
(`local_predictor.py:223-224`); con `[999]` el resultado queda vacío →
`ValueError("Prediction result must contain at least one prediction")`
(`ml/value_objects/__init__.py:126`) → HTTP 400 con ese texto técnico.
Evidencia: `local_predictor.py:215-229` (filtro y parser), `:122` (llamada);
`ml/value_objects/__init__.py:120-126`.
Clasificación: **ACCIDENTAL** (el filtro es deliberado, pero el fallo final
con mensaje interno es un efecto colateral; validación de entrada
inexistente, registro-riesgos R8).

**RN-06 — Nombres de predicción por convención `{variable}_target_{horizonte}`.**
Enunciado: la correspondencia entre salida del modelo y magnitud/horizonte
se establece por el nombre de la columna de destino.
Ejemplo: `temperature_2m_target_24` → predicción de temperatura a 24 h, bajo
la clave `predictions[24]["temperature_2m"]` (`rsplit("_target_", 1)`).
Evidencia: `train_model.py:125-131` (construcción), `local_predictor.py:215-229`
(parseo). Si una variable contuviera "_target_" en su nombre, el parseo la
rompería (p. ej. `dew_point_2m_target` hipotético) — hoy no ocurre.
Clasificación: **INTENCIONAL** (convención coherente entre train y runtime).

**RN-07 — Alineación de entradas: lo que falta vale 0, lo que sobra se
ignora, la ciudad viaja como texto.**
Enunciado: antes de predecir, las entradas se ajustan al esquema del modelo:
columnas ausentes → 0.0, columnas extra → descartadas; la columna `city`
recibe el nombre real de la ciudad (no un 0).
Ejemplo: si al modelo le falta `dew_point_2m_lag_24`, entra como 0.0; si la
ciudad es "São Paulo" (con acento y tilde), viaja tal cual al codificador.
Evidencia: `local_predictor.py:186-192` (`aligned[col] = float(features.get(col, 0.0))`,
rama `col == "city"`).
Clasificación: **INTENCIONAL** (docstring `:171-176` lo documenta).

**RN-08 — En inferencia, todos los "lags" valen lo mismo: el tiempo actual.**
Enunciado: el valor de entrada para cualquier horizonte h es siempre la
condición actual, para cada variable y horizonte.
Ejemplo: `temperature_2m_lag_6`, `_lag_12` y `_lag_24` reciben las mismas
18,5 °C actuales.
Evidencia: `feature_extractor.py:62-77` (bucle `for h in horizons: value =
current_conditions.get(var, 0.0)`).
Hallazgo (discrepancia): el entrenamiento usa el valor de **h filas antes**
(`train_model.py:100`, `shift(h)`), no el valor actual; el comentario
`feature_extractor.py:21` ("This matches the feature engineering in
scripts/train_model.py") promete una coincidencia que no es semánticamente
cierta. Clasificación: **INTENCIONAL en runtime** (comentado), con
**discrepancia documental** respecto al entrenamiento (registro-riesgos R3).

**RN-09 — Dirección del viento y punto de rocío valen siempre 0 en
inferencia.**
Enunciado: aunque el modelo se entrenó con dirección del viento y punto de
rocío reales, en inferencia esas dos variables nunca llegan: todos sus lags
entran a 0.0.
Ejemplo: en `POST /predict`, `_weather_to_conditions` solo aporta 6 claves
(`predict/handler.py:108-115`); el extractor pide 8
(`feature_extractor.py:63-72`); `wind_direction_10m_lag_6` y
`dew_point_2m_lag_6` → `0.0`. En entrenamiento sí tenían valores
(`train_model.py:30-39`, `NUMERIC_FEATURES`).
Evidencia: `feature_extractor.py:63-72,76`; `predict/handler.py:108-115`;
`train_model.py:30-39,100`.
Clasificación: **ACCIDENTAL** (nadie lo documenta; hallazgo nuevo, no
registrado antes: extensión de la anomalía §4.1 del mapa al flujo
`/predict`).

**RN-10 — El chat entrega al modelo condiciones actuales nulas.**
Enunciado: en el flujo conversacional, todas las variables del tiempo actual
(los lags) entran a 0.0 porque el diccionario que recibe el extractor usa
otras claves.
Ejemplo: "¿Lloverá mañana en Madrid?" → `to_features()` produce
`"temperature": 18.5` (`weather/repository/__init__.py:57-62`), el extractor
busca `"temperature_2m"` (`feature_extractor.py:63-72`), no está → 0.0
(`:76`); todos los lags → 0.0 (`local_predictor.py:191`).
Evidencia: `ask_agent/handler.py:157`; `weather/repository/__init__.py:50-62`;
`feature_extractor.py:63-77`; `local_predictor.py:186-192`.
Clasificación: **ACCIDENTAL** (anomalía ya registrada, mapa §4.1).

**RN-11 — La API solo expone horizontes de 6, 12 y 24 horas.**
Enunciado: aunque el modelo sabe predecir hasta 168 h, el negocio solo puede
pedir 6/12/24 por API (valores por defecto y de ejemplo).
Ejemplo: `PredictRequest` sin `horizons` → `[6, 12, 24]`; el modelo entrenado
con `[6, 12, 24, 48, 72, 168]` (`train_model.py:155`) nunca sirve 48/72/168.
Evidencia: `predict.py:32-35`; `application/predict/command.py:19`
(`default_factory=lambda: [6, 12, 24]`); `ask_agent/handler.py:160,165`
(`horizons=[6, 12, 24]`).
Clasificación: **INTENCIONAL** (constantes repetidas de forma coherente).

**RN-12 — La identidad del modelo es su huella binaria y su fecha de
fichero.**
Enunciado: la "versión" del modelo es un MD5 truncado del binario y su fecha
de entrenamiento es la fecha de modificación del fichero.
Ejemplo: copiar `model.pkl` sin cambiarlo no cambia la versión; tocarlo (o
regenerarlo) cambia ambas aunque el modelo aprendido sea idéntico.
Evidencia: `local_predictor.py:153-157` (`hashlib.md5(content).hexdigest()[:8]`),
`:159-163` (mtime).
Clasificación: **INTENCIONAL** (implementado a propósito), con nota de riesgo
(registro-riesgos R10).

**RN-13 — Sin redondeos en ningún punto.**
Enunciado: ni predicciones ni resúmenes se redondean ni truncan; el negocio
ve los decimales que salgan.
Ejemplo: temperatura predicha 18.5343994140625 → el resumen del chat imprime
`temp=18.5343994140625°C` (`f"...temp={...value}°C"`) y `/predict` devuelve
el float sin formatear.
Evidencia: `ask_agent/handler.py:248-254` (formato bruto), `predict.py:41-46`
(`float` sin transformación); no hay `round`/format en ninguna salida
(verificado por búsqueda).
Clasificación: **ACCIDENTAL** (no hay señal de decisión; el orden de
aplicación de redondeos es "ninguno").

---

## B. Entrenamiento (utilidad que genera `model.pkl`)

**RN-14 — Partición temporal 80/20 con truncamiento entero.**
Enunciado: el 20 % final de las filas (en el orden del fichero, sin
mezclar) es la prueba; el corte se trunca a entero.
Ejemplo: 100.000 filas → `int(100000 * 0.8)` = 80.000; las filas 80.001+ son
test. Con 100.005 filas → 80.004 (truncamiento, no redondeo).
Evidencia: `train_model.py:166` (`test_size: float = 0.2`), `:169-171`
(`split_idx = int(len(X) * (1 - test_size))`, `iloc` sin shuffle).
Clasificación: **INTENCIONAL** (comentario "time-aware: last portion as
test", `:165`).

**RN-15 — Los lags se construyen desplazando filas, no horas.**
Enunciado: el valor "h antes" es el de h filas antes dentro de cada ciudad;
equivale a h horas solo si el histórico es continuo y horario.
Ejemplo: si a Berlín le falta una hora del CSV, todos los lags de Berlín
desde ese punto quedan desalineados una hora respecto al reloj.
Evidencia: `train_model.py:100` (`df.groupby("city")[var].shift(h)`).
Clasificación: **DUDOSA** (la equivalencia filas=horas depende de la
continuidad del dataset, que nadie valida → pregunta; SUPOSICIÓN: el CSV es
continuo).

**RN-16 — Los objetivos son el valor futuro h filas después; las colas del
histórico se pierden.**
Enunciado: el objetivo de cada fila es el valor de la variable h filas
después en su ciudad; las h últimas filas de cada ciudad no tienen objetivo
y se descartan.
Ejemplo: con horizonte 168, las últimas 168 filas por ciudad no generan
target y desaparecen (`dropna`).
Evidencia: `train_model.py:139-141` (`shift(-h)`), `:140` (`dropna`),
`:75` (dropna de targets en carga).
Clasificación: **INTENCIONAL** (mecánica estándar de lags).

**RN-17 — Constantes de entrenamiento fijas.**
Enunciado: el modelo se entrena con valores fijos: 200 árboles, profundidad
5, tasa 0,1, submuestreo 0,8 y semilla 42.
Ejemplo: dos entrenamientos con el mismo CSV producen el mismo modelo
(determinismo por semilla), salvo cambios de entorno.
Evidencia: `train_model.py:186-193` (`n_estimators=200`, `max_depth=5`,
`learning_rate=0.1`, `random_state=42`, `subsample=0.8`); los valores por
defecto de la función `:160-163`.
Clasificación: **INTENCIONAL** (semilla explícita).

**RN-18 — Si una variable no varía en test, su R² se reporta como 0.**
Enunciado: cuando el denominador del R² (varianza) es nulo, la métrica de
esa variable se publica como 0, no como "no calculable".
Ejemplo: variable constante en test (`ss_tot == 0`) → `r2 = 0` y se loguea
"R²=0.0000" como si fuera un mal modelo.
Evidencia: `train_model.py:227-228` (`if ss_tot > 0 else 0`).
Clasificación: **ACCIDENTAL** (convención silenciosa de implementación).

---

## C. Agente conversacional (`POST /chat`)

**RN-19 — La intención se decide por subcadenas con prioridad fija:
ahora > consejo > histórico > pronóstico > general.**
Enunciado: la primera lista de palabras que aparezca como subcadena de la
pregunta (en minúsculas) decide la intención; el orden de evaluación es
estado actual, consejo, histórico y, como comodín, pronóstico.
Ejemplo (frontera por subcadena): "I want to know the weather" contiene
"now" dentro de "know" → **CURRENT_CONDITIONS** aunque sea una pregunta de
pronóstico. "Will it rain in social media" contiene "media" → **HISTORICAL**
antes que FORECAST ("rain", "will").
Evidencia: orden `query_intent.py:165-176`; listas `:19-53` (forecast),
`:55-77` (advice), `:79-92` (current), `:94-110` (historical); comparación
`kw in query_lower` (`:166-174`).
Clasificación: **INTENCIONAL** el orden (comentario `:166` "Check more
specific intents first"); **ACCIDENTAL** el efecto de subcadenas falsas
(nadie lo documenta).

**RN-20 — Pregunta no meteorológica: sin tiempo ni modelo, pero con RAG y
LLM.**
Enunciado: si la intención es "general", no se consulta el tiempo ni el
modelo, pero sí se busca en la base de conocimiento y se llama al LLM.
Ejemplo: "¿quién eres?" → intención GENERAL (`query_intent.py:175-176`) →
saltos a RAG (`handler.py:120`) → respuesta del LLM con documentos
meteorológicos de contexto.
Evidencia: `ask_agent/handler.py:110-121` (bloque condicionado),
`:118-121` (RAG incondicional).
Clasificación: **INTENCIONAL** (estructura deliberada del flujo).

**RN-21 — Pregunta histórica: se responde como si fuera de tiempo actual.**
Enunciado: las preguntas de intención histórica no consultan datos
históricos; reciben el mismo tratamiento que una de pronóstico (tiempo
actual + modelo).
Ejemplo: "¿Llovió más el año pasado en Madrid?" → intención HISTORICAL
("año pasado", `query_intent.py:99`) → `is_weather_related=True`
(`:141-147`) → `geocode` + `get_current_weather` (`handler.py:151-152`); el
método histórico de la API (`open_meteo_adapter.py:125-171`) no se llama
nunca en runtime.
Evidencia: como arriba.
Clasificación: **DUDOSA** (¿requisito pendiente o decisión? → pregunta,
memoria-histórica A4/H12).

**RN-22 — Ciudad solo con patrón "in/at/for/en + NombreCapitalizado"; gana
el primer patrón.**
Enunciado: la ciudad se extrae si va precedida de "in", "at", "for" o "en"
(según ese orden) seguida de una o más palabras con inicial mayúscula; si no
hay ciudad, no hay contexto meteorológico.
Ejemplo: "¿Qué tiempo hará en Madrid?" → patrón `en` captura "Madrid".
"¿Qué tiempo hará en madrid?" → sin match (minúscula) → caso RN-22 fallido.
"Rain in Spain and fog en Paris" → captura "Spain" (el patrón "in" va
primero).
Evidencia: `ask_agent/handler.py:83-93` (patrones en orden `:83-88`, primer
match gana `:89-92`), `:114` (`if city:`).
Clasificación: **INTENCIONAL** (docstring "simple heuristics", `:72-76`).

**RN-23 — El RAG se consulta siempre y sin umbral: los 3 primeros
documentos entran al prompt, sea cual sea su parecido.**
Enunciado: toda pregunta (metereológica o no) recupera hasta 3 documentos
por similitud coseno; no existe puntuación mínima de corte.
Ejemplo: "hola" → `top_k=3` → los 3 documentos meteorológicos "menos
improbables" se añaden como chunks `rag_document` al prompt.
Evidencia: `ask_agent/handler.py:118-121,184-205` (búsqueda incondicional,
sin filtro de score); `knowledge_base_adapter.py:69-82` (SQL ordena por
`embedding <=> :embedding`, `LIMIT :limit`); `top_k=3` por defecto
(`:69`, usado en `handler.py:192`).
Clasificación: **INTENCIONAL** (constantes explícitas), con hallazgo: la
ausencia de umbral no está documentada en ningún comentario.

**RN-24 — Una conversación es una pregunta y una respuesta; después no se
puede añadir contexto.**
Enunciado: cada sesión admite una única respuesta; una vez respondida, se
prohíbe añadir contexto; la pregunta no puede estar vacía.
Ejemplo: llamar dos veces a `generate_response` → `ValueError("Response has
already been generated")`; añadir un chunk tras responder → `ValueError`
del mismo tipo.
Evidencia: `agent/aggregate/__init__.py:39-41` (query vacía), `:54-64`
(add_context), `:67-77` (add_rag_documents), `:91-101` (generate_response).
Clasificación: **INTENCIONAL** (invariantes explícitas con mensajes).

**RN-25 — El prompt manda al LLM: instrucciones fijas en inglés + contexto
(si lo hay) + pregunta al final.**
Enunciado: el prompt se compone siempre igual: system prompt (inglés,
fijo), luego los contextos agrupados por tipo y fuente, y al final la
pregunta del usuario.
Ejemplo: sesión sin chunks → prompt = system + "## User Query" + pregunta;
sesión con weather + RAG → dos secciones "### weather_and_prediction (source:
open_meteo_and_ml)" y "### rag_document (source: knowledge_base)".
Evidencia: `ask_agent/handler.py:36-41` (system prompt), `:221-235`
(composición y orden).
Clasificación: **INTENCIONAL**.

**RN-26 — Todas las conversaciones de un proceso comparten sesión ante el
LLM.**
Enunciado: el identificador de sesión enviado al proveedor LLM se genera
una vez por arranque del servicio y se reutiliza para todos los usuarios;
cada respuesta se genera con temperatura 0,7 y máximo 1024 tokens.
Ejemplo: dos usuarios distintos en el mismo proceso → misma cabecera
`x-opencode-session` (un único UUID del singleton).
Evidencia: `opencode_go_llm.py:31-44` (UUID por instancia), `:69-76`
(`temperature: 0.7`, `max_tokens: 1024`), `di.py:64-69` (singleton).
Clasificación: **INTENCIONAL** la implementación (parámetros explícitos);
**DUDOSA** la decisión de negocio de compartir sesión (registro-riesgos R14
→ pregunta).

**RN-27 — Cada conversación genera dos eventos que se pierden.**
Enunciado: al preguntar se registra "pregunta recibida" y al responder
"respuesta generada" (con indicadores de uso de RAG y ML); ambos se
recogen y se descartan sin persistir; el indicador de uso de ML es siempre
"no" porque el contexto real se etiqueta con otro nombre.
Ejemplo: chat sobre Madrid → eventos `QueryReceived` + `ResponseGenerated`
con `used_ml_prediction=False` (el chunk es `weather_and_prediction`, el
agregado busca `ml_prediction`), y se pierden.
Evidencia: `agent/aggregate/__init__.py:56-57` (QueryReceived),
`:105-114` (ResponseGenerated; `:106` busca `"ml_prediction"`),
`ask_agent/handler.py:134-135` (pop y descarte), `:173`
(`chunk_type="weather_and_prediction"`).
Clasificación: **ACCIDENTAL** (mapa §4.2 y §4.9; flujo-aplicacion §5).

**RN-28 — La hora de las características se toma en UTC en inferencia y en
hora local (por ciudad) en entrenamiento.**
Enunciado: las variables temporales del modelo (hora, mes, día) se calculan
con la hora UTC del momento de la pregunta en inferencia; en el
entrenamiento se calcularon con la hora local del fichero histórico.
Ejemplo: pregunta a las 14:00 UTC sobre Madrid (UTC+1 invierno) →
`hour=14`; en el CSV de Madrid esa misma hora solar es `hour=15`. El modelo
ve una hora distinta de la que aprendió.
Evidencia: `feature_extractor.py:48-51` (`timestamp.hour/month/weekday`);
`ask_agent/handler.py:159` (`timestamp=session.created_at`, UTC por
defecto: `agent/aggregate/__init__.py:37`); `predict/handler.py:75`
(`datetime.now(timezone.utc)`); entrenamiento: `train_model.py:83-88`
(`df["datetime"].dt.hour` del CSV); el CSV se descargó con
`timezone=auto` (`open_meteo_adapter.py:103,149`).
SUPOSICIÓN: el `datetime` del CSV está en hora local de cada ciudad
(coherente con `timezone=auto` y con la primera fila de Berlín
00:00:00). Clasificación: **ACCIDENTAL** (nadie lo documenta; hallazgo
nuevo, no registrado antes).

---

## Resumen de clasificación

| Clase | Reglas |
|---|---|
| INTENCIONAL | RN-01, RN-02, RN-04, RN-06, RN-07, RN-08 (runtime), RN-11, RN-12, RN-14, RN-16, RN-17, RN-19 (orden), RN-20, RN-22, RN-23, RN-24, RN-25, RN-26 (implementación) |
| ACCIDENTAL | RN-05, RN-09, RN-10, RN-13, RN-18, RN-19 (subcadenas), RN-27, RN-28 |
| DUDOSA | RN-03, RN-15, RN-21, RN-26 (decisión de negocio) |

## Hallazgos nuevos respecto a documentos previos

- **RN-09** (wind_direction/dew_point a 0 en inferencia, reales en
  entrenamiento): extiende la anomalía §4.1 del mapa al flujo `/predict`,
  que se creía limpio.
- **RN-28** (UTC en inferencia vs hora local en entrenamiento): no estaba
  registrado en mapa, flujo ni riesgos.

## Preguntas para el negocio (SUPOSICIÓN → pregunta)

1. RN-03: ¿los valores por defecto (0 / 1013 hPa) son una política de
   negocio aceptada? (nombre y fecha)
2. RN-15/RN-28: ¿el CSV histórico es continuo por ciudad y está en hora
   local? ¿Quién lo garantiza? (nombre y fecha)
3. RN-21: ¿las preguntas históricas deben responderse con tiempo actual?
4. RN-26: ¿compartir sesión de LLM entre todos los usuarios es aceptado?
5. RN-11: ¿los horizontes 48/72/168 entrenados tienen algún consumidor
   previsto?
