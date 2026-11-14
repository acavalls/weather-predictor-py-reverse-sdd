# Memoria histórica — cronología extraída de los comentarios del proyecto

Fase de reconocimiento. Este documento reconstruye qué dicen los comentarios
del código sobre incidentes, decisiones, advertencias y trabajos abandonados.
**Fuente exclusiva**: comentarios, docstrings y metadatos del repositorio.
No se corrige nada (Principio III); se registran las preguntas para el
negocio (Principio II).

**Advertencia de método**: ningún comentario del código menciona personas
por nombre; los "implicados" son roles inferidos (quien entrenó el modelo,
quien integró el LLM, etc.). Las fechas son, salvo indicación, desconocidas;
los anclajes temporales disponibles son: la migración Alembic
(2026-06-08, `alembic/versions/821f93690b12_...py:5`), la ventana de datos
2023-2025 (`scripts/download_historical.py:52-53`), la fecha del binario
`models/model.pkl` (mtime 2026-11-14 10:20) y los commits de hoy
(`git log`, adopción 2026-11-14).

---

## 1. Cronología de eventos y decisiones

| # | Fecha aprox. | Qué pasó / qué se decidió | Implicados (inferidos) | Evidencia | Pregunta para el negocio |
|---|---|---|---|---|---|
| H1 | 2023-01 → 2025 | Se decide la ventana de datos de entrenamiento: histórico horario 2023-2025 para 10 ciudades fijas, con 1 s de espera entre peticiones para no saturar la API. | Quien descargó el dataset | `scripts/download_historical.py:22-34` (CITIES), `:52-54` (START_YEAR, END_YEAR, DELAY_SECONDS) | ¿Por qué esas 10 ciudades y esa ventana? ¿Fue una decisión de negocio o de comodidad de descarga? |
| H2 | Desconocida (posterior a H1) | Se decide el algoritmo: un Gradient Boosting por variable objetivo (6 variables × horizontes), envueltos en una clase propia con barra de progreso, y se pickla todo en `model.pkl` con horizontes por defecto [6, 12, 24, 48, 72, 168]. | Quien entrenó el modelo | `scripts/train_model.py:4-7` (docstring), `:146-152` (base_estimator), `:155` (horizons), `:163-171` (bucle con tqdm) | ¿Se comparó con alternativas? ¿Quién aprobó los horizontes 48/72/168, hoy inalcanzables por API (mapa §4.19)? |
| H3 | Desconocida | Incidente de integración con el LLM: el endpoint de OpenCode Go rechaza peticiones sin la cabecera `x-opencode-session` (error 400 MissingSessionID). Se decide enviar un UUID aleatorio por instancia. | Quien integró el LLM | `src/infrastructure/llm/opencode_go_llm.py:43-44` (comentario del incidente y la decisión) | ¿Cuándo ocurrió ese 400 y con qué modelo? ¿El proveedor exige sesiones por usuario final y no por proceso? |
| H4 | Desconocida | Incidente de deserialización: el modelo entrenado no cargaba porque la clase wrapper quedó picklada como `__main__`. Se decide "reescribir" `sys.modules["__main__"]` en el import del predictor para que el pickle resuelva. | Quien entrenó y quien integró el predictor | `src/infrastructure/ml/local_predictor.py:21-31` (comentario del problema y el parche) | ¿Hubo un incidente en producción por esto (log, fecha)? ¿Se evaluó repicklear el modelo en vez de parchear el runtime? |
| H5 | Desconocida | Decisión de codificación de ciudades desconocidas: `OneHotEncoder(handle_unknown="ignore")`, es decir, ciudad no vista en entrenamiento → codificación a ceros; el predictor además inyecta el nombre de la ciudad en la columna `city`. | Quien entrenó el modelo | `scripts/train_model.py:178`; `src/infrastructure/ml/local_predictor.py:173-176` (docstring que documenta la decisión) | ¿Se asume aceptable predecir para ciudades fuera del dataset con calidad desconocida? ¿Hay lista de ciudades soportadas de negocio? |
| H6 | 2026-06-08 12:45 | Se genera la migración inicial de Alembic ("initial tables: forecasts, knowledge_base, models"), pero se decide que las tablas ya las crea `init.sql` y la migración solo añade el índice IVFFLAT de pgvector. | Quien montó la base de datos | `alembic/versions/821f93690b12_initial_tables_...py:1-5` (nombre y Create Date), `:20` ("Tables already exist via init.sql") | ¿Por qué dos mecanismos de esquema (`init.sql` + Alembic)? ¿Cuál es la fuente de verdad oficial? |
| H7 | Desconocida | Decisión de modelo de lenguaje: usar el endpoint "OpenCode Go" con el modelo `mimo-v2.6-flash` como valores por defecto de la configuración. | Quien eligió el proveedor LLM | `src/infrastructure/config/settings.py:11-12`; `src/infrastructure/llm/opencode_go_llm.py:34-35` | ¿Quién aprobó ese proveedor/modelo y su coste? ¿Hay alternativa contratada? |
| H8 | Desconocida | Decisión de embeddings locales: modelo `all-MiniLM-L6-v2` (384 dimensiones) tanto en runtime como en la ingesta; la dimensión 384 queda grabada en el esquema (`vector(384)`). | Quien montó el RAG | `src/infrastructure/embedding/local_embedder.py:16,22`; `scripts/ingest_knowledge.py:29-30`; `init.sql:20` (`embedding vector(384)`) | ¿Se evaluó un modelo de embeddings mayor/mejor? Cambiarlo exige regenerar tabla e índice: ¿quién decide eso? |
| H9 | Desconocida | Decisión de interfaz: UI de chat "estilo ChatGPT" servida desde el propio servicio en `GET /`. | Quien hizo la interfaz | `src/main.py:47` ("Serve the ChatGPT-style weather agent UI"); `chat.html:1-6` | ¿Es la UI actual la definitiva o una maqueta de demostración? |
| H10 | Desconocida | Decisión de clasificador de intenciones "simple": palabras clave en inglés y español; el comentario admite que "en producción esto usaría un modelo NLP o el LLM". | Quien implementó el agente | `src/domain/agent/value_objects/query_intent.py:154-155` | ¿Se considera la clasificación por palabras clave aceptable para producción? ¿Hay tickets/planes para sustituirla? |
| H11 | Desconocida | Decisión de extracción de ciudad "simple": heurística regex para "in/at/for/en + Nombre", con mayúscula inicial obligatoria. | Quien implementó el agente | `src/application/ask_agent/handler.py:72-76` (docstring "simple heuristics") | ¿Se conoce su tasa de fallo con preguntas reales de los usuarios? |
| H12 | Desconocida | Advertencia de coordinación: el extractor de características en runtime "debe coincidir" con la ingeniería del entrenamiento ("This matches the feature engineering in scripts/train_model.py"). | Quien entrenó y quien integró el runtime | `src/infrastructure/ml/feature_extractor.py:21` | ¿Existe algún test o proceso que verifique esa coincidencia? (Hoy no hay tests.) |

---

## 2. Advertencias del tipo "no tocar"

| # | Advertencia y motivo declarado | Implicados | Evidencia | Pregunta para el negocio |
|---|---|---|---|---|
| W1 | "This class is pickled inside model.pkl. It MUST remain importable from this module path for joblib.load() to deserialize the model correctly." — no mover ni renombrar `MultiOutputRegressorWithProgress`. | Quien entrenó el modelo | `src/infrastructure/ml/model_wrapper.py:1-8` | ¿Quién es el responsable de volver a generar `model.pkl` si algún día hay que tocar la clase? |
| W2 | El wrapper reescribe `sys.modules["__main__"]` en el import de `local_predictor` (efecto global en el proceso): touching esa zona afecta a todo el runtime. | Quien integró el predictor | `src/infrastructure/ml/local_predictor.py:21-31` | ¿Se conoce el efecto de ese parche sobre otros `__main__` futuros (scripts, tests)? |
| W3 | "The OpenCode Go endpoint rejects requests without x-opencode-session (400 MissingSessionID)" — la cabecera es obligatoria; no quitarla. | Quien integró el LLM | `src/infrastructure/llm/opencode_go_llm.py:43-44` | ¿Qué pasa si el proveedor cambia el requisito? ¿Hay contrato de soporte con ese proveedor? |
| W4 | `handle_unknown="ignore"` + ciudad inyectada en la columna `city`: el comportamiento con ciudades desconocidas es "consciente" y documentado; cambiarlo altera las predicciones silenciosamente. | Quien entrenó el modelo | `scripts/train_model.py:178`; `src/infrastructure/ml/local_predictor.py:173-176` | ¿Se ha medido el error de predicción para ciudades fuera del dataset? |

---

## 3. Trabajos abandonados o a medias

| # | Qué se empezó y dónde quedó | Implicados | Evidencia | Pregunta para el negocio |
|---|---|---|---|---|
| A1 | Migración de prueba "test_migration" (id `320b6a04018d`) generada y borrada; solo queda su bytecode en caché dentro del repositorio. | Quien preparó Alembic | `alembic/versions/__pycache__/320b6a04018d_test_migration.cpython-38.pyc` (binario, contiene la cadena "320b6a04018d"); no existe el `.py` correspondiente en `alembic/versions/` | ¿Fue una prueba de `make db-migrate`? ¿Hay convención de limpieza de migraciones de prueba? |
| A2 | Tabla `forecasts` creada "optional, for prediction history" y su ORM `ForecastModel`: nunca se escribe ni se lee en runtime. | Quien montó la persistencia | `init.sql:3` ("optional, for prediction history") y `:4-18`; `src/infrastructure/persistence/models/forecast.py:13-34` | ¿Se quiere guardar el historial de predicciones? ¿Es requisito pendiente o descartado? |
| A3 | Tabla `models` con métricas JSONB (`TrainedModelModel`): creada y mapeada, sin escritor ni lector. | Quien montó la persistencia | `init.sql:32-39`; `src/infrastructure/persistence/models/model.py:13-24` | ¿Quién iba a registrar las versiones/métricas de los modelos ahí? ¿Por qué no se conectó con `train_model.py`? |
| A4 | Agregado de dominio `Forecast` con ciclo de vida y eventos (`ForecastRequested`/`ForecastGenerated`): implementado completo, nunca instanciado por ningún caso de uso. | Quien diseñó el dominio del tiempo | `src/domain/weather/aggregate/__init__.py:23-147`; `src/domain/weather/events/__init__.py:18-45` | ¿Se prevé un flujo "forecast" distinto del chat que lo use, o se abandona? |
| A5 | Eventos de sesión (`QueryReceived`, `ResponseGenerated`) recogidos y después descartados en cada petición de chat: la promesa del agregado ("Collects domain events as state changes occur") no tiene consumidor. | Quien diseñó el agente | `src/domain/agent/aggregate/__init__.py:37-38` (promesa), `:56-57,105-114` (eventos); `src/application/ask_agent/handler.py:134-135` (descarte) | ¿Debían persistirse o publicarse (auditoría, analítica)? ¿Qué decisión lo paró? |
| A6 | `get_session`/`get_session_factory` en la capa de persistencia: docstring "Intended for FastAPI dependency injection", sin llamadores en runtime (el adaptador RAG construye su propia sesión). | Quien montó la persistencia | `src/infrastructure/persistence/session.py:42-50`; `src/infrastructure/persistence/knowledge_base_adapter.py:34-37` | ¿Se planeaba inyectar sesiones por request en FastAPI? ¿Por qué el adaptador no lo usa? |
| A7 | Puertos con implementaciones anunciadas que nunca existieron: `MeteostatAdapter`, `MockWeatherProvider`, `RemoteEmbedder`, `RemotePredictor`, `CachedFeatureExtractor`, `ChromaDBAdapter`, `InMemoryVectorStore`. | Quien diseñó los puertos | `weather/repository/__init__.py:69`; `agent/repository/embedder.py:10`; `ml/repository/__init__.py:15,67`; `agent/repository/vector_store.py:12` | ¿Eran planes reales (proveedor alternativo, embeddings remotos, caché) o plantas teóricas? ¿Alguna sigue viva? |
| A8 | `MockLLM` y `NullLogger` preparados "for testing and development" pero sin cablear en el contenedor DI ni usados en tests (no hay tests). | Quien preparó el entorno de pruebas | `src/infrastructure/llm/mock_llm.py:1-11`; `src/infrastructure/logging/adapter.py:38-54`; `di.py:64-69` (cablea siempre el real) | ¿Se planeaba un perfil de pruebas del contenedor DI? ¿Cuándo se harán los tests? |
| A9 | `respx` (mock de httpx) declarado en dependencias sin ningún test que lo use. | Quien preparó el entorno de pruebas | `requirements.txt:33`; sin directorio `tests/` | ¿Hubo una fase de tests anterior que se perdió, o nunca se empezó? |
| A10 | Clasificador de intenciones "en producción usaría un modelo NLP o el LLM": mejora prometida en el comentario, nunca emprendida. | Quien implementó el agente | `src/domain/agent/value_objects/query_intent.py:154-155` | ¿Está planificada esa mejora? ¿Con qué prioridad? |
| A11 | `README.md` (0 bytes) y `docs/` (vacío): la documentación del proyecto nunca se escribió. | El proyecto entero | `README.md` (vacío); `docs/` (sin contenido) | ¿Hubo documentación previa en otro sitio? |
| A12 | Alternativas de proveedor de tiempo (Meteostat) y de base vectorial (ChromaDB) citadas en docstrings como implementaciones posibles: nunca se iniciaron. | Quien diseñó los puertos | `weather/repository/__init__.py:69`; `agent/repository/vector_store.py:12` | ¿Hubo evaluación de proveedores? ¿Por qué se cerró con Open-Meteo + pgvector? |

---

## 4. Hechos de contexto (sin pregunta asociada)

- El dataset de entrenamiento arranca el 2023-01-01 00:00:00 (primera fila de
  datos de `data/historical_weather.csv`, 263.040 filas de datos).
- La migración inicial de Alembic se creó el 2026-06-08 12:45:54
  (`alembic/versions/821f93690b12_...py:5`).
- El binario `models/model.pkl` tiene mtime 2026-11-14 10:20 (misma mañana que
  la adopción de la constitución): el modelo actual se (re)generó ese día.
- La historia de Git arranca en la adopción (commit raíz `4a26937`,
  2026-11-14): no hay arqueología de commits anterior; toda la memoria
  pre-adopción vive solo en los comentarios aquí extraídos.
- Ningún comentario del código menciona personas, equipos ni tickets
  (búsqueda de TODO/FIXME/XXX/HACK/nombres: sin resultados relevantes;
  evidencia: `grep -riE 'TODO|FIXME|XXX|HACK' src scripts` sin coincidencias
  de trabajo pendiente).

## 5. Preguntas abiertas consolidadas

Para llevar a sesión con el negocio (todas requieren testimonio con nombre y
fecha): H1-H12, W1-W4, A1-A12. Las tres de mayor prioridad por su impacto en
la fase actual: **H2/H4** (procedencia y reproducibilidad de `model.pkl`),
**H3** (contrato con el proveedor LLM) y **A2/A3** (destino de las tablas
sin uso: requisito pendiente o descartado).
