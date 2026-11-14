# Mapa del Sistema — weather-agent

Fase de reconocimiento. Documento de caracterización: describe el sistema tal
como es hoy, sin corregir nada. Toda afirmación lleva su evidencia
(fichero y líneas) conforme a la constitución
(`.specify/memory/constitution.md`, Principio II).

Evidencia base: inspección de código de `src/`, `scripts/`, `alembic/`,
`init.sql`, `docker-compose.yml`, `requirements.txt`, `pyproject.toml`,
`Makefile` y del entorno virtual `venv/` (commit `27bcbcd`, 2026-11-14).

---

## 1. Módulos y ficheros relevantes

### 1.1 Capa HTTP (entrada del sistema)

| Fichero | Responsabilidad (negocio) | Depende de | Dependen de él | Criticidad |
|---|---|---|---|---|
| `src/main.py` | Es la puerta del servicio: arranca la aplicación web que atiende preguntas del tiempo y sirve la página de chat. | Rutas HTTP (`main.py:28-30`), `chat.html` (`main.py:36-41`) | Despliegue (`make dev`, `Makefile:9`) | **Alta**: sin él no hay servicio (`src/main.py:23-30`) |
| `src/infrastructure/http/routes/chat.py` | Recibe la pregunta del usuario en lenguaje natural y devuelve la respuesta conversacional del agente. | Puerto `IAskAgentUseCase` (`chat.py:11,42-44`), contenedor DI (`chat.py:13`) | `src/main.py:30` | **Alta**: es la función principal del producto (`chat.py:47-53`) |
| `src/infrastructure/http/routes/predict.py` | Expone la predicción numérica del tiempo para una ciudad a 6, 12 y 24 horas. | Puerto `IPredictUseCase` (`predict.py:11,18-20`), contenedor DI (`predict.py:13`) | `src/main.py:29` | **Media**: endpoint declarado como "debug" en su propia cabecera (`predict.py:1`) |
| `src/infrastructure/http/routes/health.py` | Permite comprobar que el servicio está vivo. | Nada (FastAPI only) | `src/main.py:28` | **Baja**: devuelve literal `{"status": "ok"}` (`health.py:12-14`) |
| `src/infrastructure/http/static/chat.html` | Es la interfaz web donde el usuario escribe y lee las respuestas del agente. | `POST /chat` (llamada AJAX desde el navegador) | `src/main.py:36-48` | **Media**: única UI del producto |

### 1.2 Capa de aplicación (casos de uso)

| Fichero | Responsabilidad (negocio) | Depende de | Dependen de él | Criticidad |
|---|---|---|---|---|
| `src/application/ask_agent/handler.py` | Orquesta la conversación: entiende la pregunta, consulta el tiempo, predice, busca en la base de conocimiento y redacta la respuesta con un LLM. | `WeatherProvider`, `ModelPredictor`, `FeatureExtractor`, `VectorStore`, `Embedder`, `LLMProvider`, `Logger` (`handler.py:43-53`) | `di.py:80-90`, `chat.py:11` | **Alta**: núcleo del agente conversacional |
| `src/application/ask_agent/port.py` y `command.py` | Definen el contrato de entrada/salida del caso de uso conversacional. | `command.py` (`port.py:8`) | `handler.py:8-9`, `chat.py:10-11` | **Baja**: contrato puro, sin lógica |
| `src/application/predict/handler.py` | Calcula la predicción numérica: geolocaliza la ciudad, lee el tiempo actual y aplica el modelo entrenado. | `WeatherProvider`, `ModelPredictor`, `FeatureExtractor` (`handler.py:29-36`) | `di.py:72-78`, `predict.py:10-11` | **Alta**: único camino hacia las predicciones del modelo |

### 1.3 Capa de dominio (reglas y contratos)

| Fichero | Responsabilidad (negocio) | Depende de | Dependen de él | Criticidad |
|---|---|---|---|---|
| `src/domain/weather/value_objects/__init__.py` | Representa las magnitudes del tiempo (temperatura, humedad, presión, viento, nubes, lluvia) con sus límites físicos. | Nada | `open_meteo_adapter.py:17-25`, `weather/repository` | **Media**: toda medida pasa por aquí |
| `src/domain/weather/repository/__init__.py` | Contrato de quién proporciona los datos del tiempo + objeto `CurrentWeather`. | value_objects (`repository/__init__.py:8-15`) | `open_meteo_adapter.py:16`, `ask_agent/handler.py:16`, `predict/handler.py:12` | **Alta**: contrato del dato más importante |
| `src/domain/weather/aggregate/__init__.py` | Agregado `Forecast`: ciclo de vida de una predicción solicitada→generada con eventos. | events, value_objects (`aggregate/__init__.py:10-18`) | **Nadie en runtime** (ver §4 Zonas oscuras) | **Baja**: sin uso |
| `src/domain/weather/services/__init__.py` | `WeatherInterpretationService`: interpreta condiciones (¿lloverá?, nivel de presión) en lenguaje cualitativo. | value_objects (`services/__init__.py:6`) | **Nadie** | **Baja**: sin uso |
| `src/domain/weather/events/__init__.py` | Registra hechos del negocio (predicción solicitada/generada). | Nada | `weather/aggregate` | **Baja**: solo usados por el agregado sin uso |
| `src/domain/ml/repository/__init__.py` | Contratos del predictor y del extractor de características. | value_objects ML (`repository/__init__.py:8`) | `local_predictor.py:16`, `feature_extractor.py:9`, ambos handlers | **Alta**: contratos del ML |
| `src/domain/ml/value_objects/__init__.py` | Representa el conjunto de características, la versión del modelo y el resultado de predicción. | Nada | `local_predictor.py:17`, `feature_extractor.py:10`, handlers | **Alta**: esquema del modelo |
| `src/domain/agent/aggregate/__init__.py` | `ChatSession`: ciclo de vida de una conversación (pregunta → contexto → respuesta) con eventos. | events, value_objects agent (`aggregate/__init__.py:9-11`) | `ask_agent/handler.py:10` | **Media**: da forma a la sesión, pero sus eventos se descartan (`ask_agent/handler.py:134-135`) |
| `src/domain/agent/repository/{embedder,llm_provider,vector_store}.py` | Contratos para generar embeddings, hablar con el LLM y buscar en la base de conocimiento. | value_objects agent (`vector_store.py:6`) | `local_embedder.py:9`, `opencode_go_llm.py:11`, `mock_llm.py:8`, `knowledge_base_adapter.py:12`, `ask_agent/handler.py:11` | **Alta**: contratos del agente |
| `src/domain/agent/value_objects/query_intent.py` | Clasifica la pregunta del usuario (pronóstico, estado actual, consejo, histórico, general) por palabras clave en inglés y español. | Nada | `ask_agent/handler.py:12,107` | **Media**: decide si se consulta el tiempo |
| `src/domain/agent/value_objects/{context_chunk,retrieved_document}.py` | Representan los trozos de contexto y los documentos recuperados para responder. | Nada | `ask_agent/handler.py:12`, `knowledge_base_adapter.py:13` | **Media** |
| `src/domain/agent/value_objects/location_query.py` | Representa una ubicación extraída de la pregunta. | Nada | **Nadie** (solo re-export en `value_objects/__init__.py:4`) | **Baja**: sin uso |
| `src/domain/agent/events/__init__.py` | Hechos de la conversación (pregunta recibida, respuesta generada). | Nada | `agent/aggregate` | **Baja** |
| `src/domain/shared/errors/__init__.py` | Errores comunes del dominio (validación, no encontrado). | Nada | rutas HTTP, adaptadores | **Baja** |
| `src/domain/shared/logger.py` | Contrato de registro de sucesos para el núcleo. | Nada | `logging/adapter.py:6`, `ask_agent/handler.py:15` | **Baja** |

### 1.4 Capa de infraestructura (adaptadores)

| Fichero | Responsabilidad (negocio) | Depende de | Dependen de él | Criticidad |
|---|---|---|---|---|
| `src/infrastructure/config/di.py` | Cablea qué servicio concreto hace cada papel (proveedor de tiempo, predictor, LLM, etc.). | Todos los adaptadores y handlers (`di.py:11-21`) | rutas HTTP (`chat.py:13`, `predict.py:13`) | **Alta**: punto único de cableado (`di.py:93`) |
| `src/infrastructure/config/settings.py` | Configuración del sistema leída de variables de entorno. | `pydantic_settings` (`settings.py:3`) | `di.py:13`, `session.py:9` | **Alta**: de aquí salen credenciales y URLs (`settings.py:9-16`) |
| `src/infrastructure/weather/open_meteo_adapter.py` | Obtiene del servicio externo Open-Meteo la geolocalización, el tiempo actual y el histórico. | puerto `WeatherProvider`, `httpx` (`open_meteo_adapter.py:13-16`) | `di.py:39-42` → ambos handlers | **Alta**: única fuente de datos meteorológicos |
| `src/infrastructure/ml/local_predictor.py` | Carga el modelo entrenado (`model.pkl`) y produce las predicciones numéricas. | puerto `ModelPredictor`, `joblib`, `pandas`, `model_wrapper` (`local_predictor.py:12-19`) | `di.py:44-47` → ambos handlers | **Alta**: motor de predicción |
| `src/infrastructure/ml/feature_extractor.py` | Convierte el tiempo actual + la hora en las variables que entiende el modelo. | puerto `FeatureExtractor` (`feature_extractor.py:9`) | `di.py:49-51` → ambos handlers | **Alta**: sin él el modelo no recibe entrada válida |
| `src/infrastructure/ml/model_wrapper.py` | Clase envoltorio guardada dentro del fichero del modelo entrenado. | `numpy`, `sklearn` (solo en `score`, `model_wrapper.py:29-31`) | `local_predictor.py:19`, `scripts/train_model.py:26` | **Alta**: si cambia de sitio, `model.pkl` deja de cargar (`local_predictor.py:21-31`) |
| `src/infrastructure/llm/opencode_go_llm.py` | Habla con el servicio de lenguaje (OpenCode Go) para redactar la respuesta. | puerto `LLMProvider`, `httpx` (`opencode_go_llm.py:9-11`) | `di.py:64-69` | **Alta**: sin LLM no hay respuesta conversacional |
| `src/infrastructure/llm/mock_llm.py` | LLM de mentira con respuestas fijas, para pruebas. | puerto `LLMProvider` (`mock_llm.py:8`) | **Nadie en runtime** | **Baja**: sin uso en producción |
| `src/infrastructure/embedding/local_embedder.py` | Convierte texto en vectores numéricos para buscar documentos parecidos. | puerto `Embedder`, `sentence_transformers` (`local_embedder.py:7-9`) | `di.py:60-62` | **Media**: solo lo usa el flujo conversacional |
| `src/infrastructure/persistence/knowledge_base_adapter.py` | Guarda y busca los documentos meteorológicos por similitud en la base de datos. | puerto `VectorStore`, SQLAlchemy async, `KnowledgeBaseModel` (`knowledge_base_adapter.py:9-14`) | `di.py:55-58` | **Media**: alimenta el contexto RAG |
| `src/infrastructure/persistence/session.py` | Conexión a la base de datos PostgreSQL. | `settings` (`session.py:9`) | `knowledge_base_adapter.py` (vía `di.py:53-58`), `alembic/env.py` | **Media** |
| `src/infrastructure/persistence/models/{base,forecast,knowledge_base,model}.py` | Definición de las tablas `forecasts`, `knowledge_base` y `models`. | `base.py` | `knowledge_base_adapter.py:14`, `alembic` | **Baja-Media**: solo `knowledge_base` se usa en runtime (ver §4) |
| `src/infrastructure/logging/adapter.py` | Registro de sucesos en fichero/consola. | puerto `Logger` (`adapter.py:6`) | `di.py:34-37` | **Baja** |

### 1.5 Scripts, datos y despliegue

| Fichero | Responsabilidad (negocio) | Depende de | Dependen de él | Criticidad |
|---|---|---|---|---|
| `scripts/download_historical.py` | Descarga el histórico meteorológico (2023-2025, 10 ciudades) desde Open-Meteo. | `httpx`, `pandas` (`download_historical.py:17-19`) | — | **Media**: alimenta el entrenamiento |
| `scripts/train_model.py` | Entrena el modelo de predicción multi-variable a partir del histórico y genera `model.pkl`. | `scikit-learn`, `joblib`, `pandas`, `tqdm`, `model_wrapper` (`train_model.py:20-28`) | — | **Alta**: sin reentrenar, el modelo queda congelado |
| `scripts/ingest_knowledge.py` | Carga en la base de datos los ~23 documentos meteorológicos que alimentan las respuestas. | `psycopg2`, `pgvector`, `sentence_transformers` (`ingest_knowledge.py:19-21`) | — | **Media**: sin él el RAG responde sin contexto |
| `data/historical_weather.csv` | Datos históricos de entrenamiento (263.040 filas de datos + cabecera). | — | `train_model.py` | **Media** |
| `models/model.pkl` | El modelo entrenado (3,6 MB); activo de negocio congelado. | `model_wrapper.py` (pickled) | `local_predictor.py` | **Alta**: es el cerebro predictivo |
| `docker-compose.yml` | Base de datos PostgreSQL con extensión de vectores, lista para usar. | imagen `pgvector/pgvector:pg16` (`docker-compose.yml:3`) | `session.py`, `ingest_knowledge.py` | **Media** |
| `init.sql` | Crea las tablas (`forecasts`, `knowledge_base`, `models`) y el índice de vectores. | — | PostgreSQL en docker | **Media** |
| `alembic/` + `alembic.ini` | Control de versiones del esquema de base de datos (1 migración). | `session.py` (env), tablas de `init.sql` | `make db-migrate`/`db-upgrade` (`Makefile:35-39`) | **Baja-Media** |
| `Makefile` | Comandos de operación del proyecto (instalar, arrancar, testear, migrar). | `venv/`, `docker compose` | desarrollador/agentes | **Media** |

---

## 2. Diagrama de dependencias (texto)

```text
                         ┌────────────────────────────── NAVEGADOR ──────────────────────────────┐
                         │  chat.html (src/infrastructure/http/static/chat.html)                │
                         └──────────────┬───────────────────────────────────────────────────────┘
                                        │
                                 src/main.py (FastAPI)
                          ┌─────────────┼────────────────┐
                          ▼             ▼                ▼
                   routes/health  routes/predict   routes/chat
                                       │                │
                                       │  (puertos de   │
                                       │   aplicación)  │
                                       ▼                ▼
                          PredictHandler        AskAgentHandler ─────────┐
                          (application/         (application/            │
                           predict/)             ask_agent/)             │
                               │                     │                    │
        ┌──────────────────────┼─────────────────────┼────────────────────┤
        │        (puertos de dominio, inyectados por di.py)                 │
        ▼                      ▼                     ▼                    ▼
  WeatherProvider      ModelPredictor /       VectorStore +         LLMProvider
  (domain/weather)     FeatureExtractor       Embedder              (domain/agent)
        │              (domain/ml)                │                    │
        ▼                      ▼                 ▼                    ▼
  OpenMeteoAdapter      LocalPredictor    KnowledgeBaseAdapter  OpenCodeGoLLM
  (infrastructure/      LocalEmbedder
   weather)             (infrastructure/ml)      │
        │                      ▲                ▼
        │                      │        PostgreSQL + pgvector
        │               models/model.pkl  (docker-compose.yml,
        │                       ▲          init.sql, alembic/)
        │                       │
        │            model_wrapper.py (picklado dentro del .pkl)
        │
        ▼
  API externa Open-Meteo (geocoding + forecast + archive)

  Cadena offline (no arranca con el servicio):
  download_historical.py → data/historical_weather.csv → train_model.py → model.pkl
  ingest_knowledge.py → tabla knowledge_base
```

---

## 3. Tecnologías y versiones reales

Declaradas en `requirements.txt:1-33` y verificadas contra el entorno
instalado (`venv/bin/pip list`, Python 3.8.10 — evidencia: salida de
`venv/bin/python --version` y `alembic/versions/__pycache__/*.cpython-38.pyc`):

| Tecnología | Versión instalada | Declarada como | Uso |
|---|---|---|---|
| Python | 3.8.10 | `pyproject.toml:60` (`target-version = "py38"`), `pyproject.toml:66` (mypy 3.8) | runtime |
| FastAPI | 0.124.4 | `requirements.txt:2` | API HTTP |
| Uvicorn | 0.33.0 | `requirements.txt:3` | servidor |
| scikit-learn | 1.3.2 | `requirements.txt:6` | modelo ML |
| sentence-transformers | 3.2.1 | `requirements.txt:7` | embeddings |
| NumPy | 1.24.4 | `requirements.txt:8` | cálculo numérico |
| pandas | 2.0.3 | `requirements.txt:9` | datos de entrenamiento |
| SQLAlchemy | 2.0.50 | transitiva (no declarada) | ORM async |
| asyncpg | 0.30.0 | transitiva (no declarada) | driver PostgreSQL async (`settings.py:9`) |
| psycopg2-binary | (instalada; usada por `scripts/ingest_knowledge.py:19`) | `requirements.txt:12` | driver PostgreSQL sync (scripts) |
| pgvector | 0.3.6 | `requirements.txt:13` | búsqueda vectorial |
| httpx | 0.28.1 | `requirements.txt:16` | cliente HTTP |
| pydantic / pydantic-settings | 2.10.6 / 2.8.1 | `requirements.txt:19-20` | esquemas y configuración |
| dependency-injector | 4.49.0 | `requirements.txt:23` | contenedor DI |
| Alembic | 1.14.1 | transitiva (no declarada) | migraciones (`Makefile:35-39`) |
| joblib | 1.4.2 | transitiva de scikit-learn (no declarada) | carga de `model.pkl` (`local_predictor.py:12`) |
| tqdm | 4.67.3 | transitiva (no declarada) | progreso de entrenamiento (`train_model.py:28`) |
| ruff / mypy | 0.15.14 / 1.14.1 | `requirements.txt:26-27` | calidad |
| pytest (+mock, cov, asyncio) | 8.3.5 (+…) | `requirements.txt:28-32` | tests (sin tests aún) |
| respx | 0.23.1 | `requirements.txt:33` | mock de httpx (sin uso aún) |
| PostgreSQL | 16 (imagen `pgvector/pgvector:pg16`, `docker-compose.yml:3`) | — | base de datos |

Modelos externos consumidos:
- Open-Meteo (geocoding, forecast, archive) — `open_meteo_adapter.py:44-45,139`.
- LLM "mimo-v2.6-flash" vía OpenCode Go — `opencode_go_llm.py:34-35`, `settings.py:11-12`.
- Embeddings "all-MiniLM-L6-v2" (384 dims, descargado localmente) — `local_embedder.py:22`, `settings.py:15`.

---

## 4. Zonas oscuras

Hallazgos registrados, no corregidos (Principio III). Clasificación:
[ANOMALÍA] comportamiento sospechoso · [MUERTO] código sin uso ·
[HUÉRFANO] fichero/artefacto suelto · [RIESGO] riesgo operativo ·
[A MEDIAS] funcionalidad incompleta.

1. **[ANOMALÍA] En el chat, todas las variables de entrada al modelo valen 0.**
   `AskAgentHandler` pasa a las características el resultado de
   `current_weather.to_features()` (`ask_agent/handler.py:157`), que produce
   claves `"temperature"`, `"humidity"`, `"pressure"`, `"wind_speed"`…
   (`weather/repository/__init__.py:57-62`), pero el extractor espera claves
   de Open-Meteo (`"temperature_2m"`, `"relative_humidity_2m"`, …,
   `feature_extractor.py:63-72`). El `.get(var, 0.0)` del extractor
   (`feature_extractor.py:76`) y del predictor (`local_predictor.py:191`)
   rellena todo con 0.0. `PredictHandler` en cambio usa las claves correctas
   (`predict/handler.py:108-115`). Las predicciones del flujo conversacional
   parten, por tanto, de un estado meteorológico nulo.

2. **[ANOMALÍA] El evento de respuesta dice siempre que no se usó predicción
   ML.** `ChatSession.generate_response` busca chunks de tipo
   `"ml_prediction"` (`agent/aggregate/__init__.py:106`), pero el handler
   añade el contexto como `"weather_and_prediction"` (`ask_agent/handler.py:173`).
   `used_ml_prediction` es por tanto siempre `False` (`agent/aggregate/__init__.py:113`).

3. **[MUERTO] Agregado `Forecast` y su evento**: definido en
   `domain/weather/aggregate/__init__.py:23-147` y
   `domain/weather/events/__init__.py:22-45`; ninguna ruta, handler o script
   lo instancia.

4. **[MUERTO] `WeatherInterpretationService`**: `domain/weather/services/__init__.py:8-89`,
   sin llamadas desde ninguna capa.

5. **[MUERTO] `LocationQuery`**: `domain/agent/value_objects/location_query.py:11`,
   solo re-exportado (`value_objects/__init__.py:4,8`), nunca construido.

6. **[MUERTO] `MockLLM` y `NullLogger`**: exportados
   (`infrastructure/llm/__init__.py:6`, `logging/__init__.py:3,5`) pero el
   contenedor DI cablea siempre `OpenCodeGoLLM` (`di.py:64-69`) y
   `LoggingAdapter` (`di.py:34-37`).

7. **[MUERTO] Tablas `forecasts` y `models` sin escritor**: creadas en
   `init.sql:4-33` y mapeadas (`persistence/models/forecast.py:13`,
   `persistence/models/model.py:13`), pero ningún código de runtime inserta
   ni lee en ellas; el único adaptador persistente es `knowledge_base_adapter.py`.

8. **[MUERTO] Métodos de puerto sin llamador**: `get_model_version`
   (`ml/repository/__init__.py:44-52`, implementado en `local_predictor.py:130-151`),
   `get_historical_weather` en runtime (`open_meteo_adapter.py:125-171`, solo
   lo usaría el entrenamiento offline), los getters de `PredictionResult`
   (`ml/value_objects/__init__.py`, `get_temperature`… `get_precipitation`) y
   `get_session`/`get_session_factory` (`persistence/session.py:29-50`).

9. **[MUERTO] Eventos de sesión descartados**: `pop_events()` se llama y su
   resultado no se persiste ni publica (`ask_agent/handler.py:134-135`).

10. **[RIESGO] Dependencias usadas pero no declaradas**: el código importa
    `joblib` (`local_predictor.py:12`, `train_model.py:20`), `tqdm`
    (`train_model.py:28`), `asyncpg` (URL en `settings.py:9`) y `alembic`
    (`Makefile:35-39`), pero ninguno aparece en `requirements.txt:1-33`;
    funcionan por ser dependencias transitivas o por instalación manual, lo
    que hace frágil una instalación limpia.

11. **[RIESGO] Acoplamiento binario con `model.pkl`**: la clase
    `MultiOutputRegressorWithProgress` vive en dos rutas a la vez: el
    entrenamiento la pickla como `__main__` (`train_model.py:26`) y el
    predictor reescribe `sys.modules["__main__"]` al importar para que el
    unpickling funcione (`local_predictor.py:21-31`). Mover o renombrar esa
    clase inutiliza el modelo actual.

12. **[ANOMALÍA] La fecha de entrenamiento del modelo no es real**: se toma
    del `mtime` del fichero (`local_predictor.py:159-163`), no de un dato del
    artefacto; y la "versión" es un MD5 truncado del binario
    (`local_predictor.py:153-157`).

13. **[A MEDIAS] El RAG se ejecuta para toda pregunta, incluso no
    meteorológicas**: la intención `GENERAL` no corta el flujo; siempre se
    consulta la base de conocimiento y el LLM (`ask_agent/handler.py:118-130`),
    y la extracción de ciudad solo cubre patrones "in/at/for/en" con inicial
    mayúscula (`ask_agent/handler.py:83-93`).

14. **[A MEDIAS] Capa de tests anunciada pero inexistente**: `pyproject.toml:56-61`
    configura pytest con `testpaths = ["tests"]` y `requirements.txt:28-33`
    declara pytest/respx, pero el directorio `tests/` no existe
    (`make test`, `Makefile:22`, fallaría sin destino de cobertura).

15. **[HUÉRFANO] `README.md` vacío** (0 bytes) y **`docs/` vacío**: sin
    documentación de arranque.

16. **[HUÉRFANO] Migración fantasma en caché**:
    `alembic/versions/__pycache__/320b6a04018d_test_migration.cpython-38.pyc`
    existe, pero no hay ningún fichero de migración `320b6a04018d` en
    `alembic/versions/`; restos de una migración de prueba borrada.

17. **[HUÉRFANO] Cachés de bytecode en repositorio**: `scripts/__pycache__/`
    y `alembic/versions/__pycache__/` están commiteados (no cubiertos por
    `.gitignore`, que solo ignora `__pycache__/` raíz).

18. **[RIESGO] Credenciales por defecto**: usuario/contraseña
    `weather/weather` en `docker-compose.yml:6-8` y URL de base de datos por
    defecto con esas credenciales en `settings.py:9`; `llm_api_key` por
    defecto vacío (`settings.py:10`), con lo que el chat falla si no se
    configura `.env`.

19. **[A MEDIAS] Horizontes entrenados vs. servidos**: el modelo se entrena
    para horizontes `[6, 12, 24, 48, 72, 168]` (`train_model.py:155`), pero
    tanto el endpoint como el chat fijan `[6, 12, 24]`
    (`predict.py:33-35`, `ask_agent/handler.py:160,165`); el resto de
    horizontes del modelo no son alcanzables vía API (`local_predictor.py:223-224`
    los filtra).

---

## 5. Preguntas abiertas (SUPOSICIÓN → pregunta)

- **SUPOSICIÓN**: `predict.py:1` llama a `POST /predict` "debug endpoint";
  se supone que es un endpoint interno. *¿Es así o es funcionalidad de
  negocio expuesta?* Requiere testimonio del negocio (nombre y fecha).
- **SUPOSICIÓN**: los datos de `data/historical_weather.csv` empiezan en
  2023-01-01 (cabecera, línea 2) y cubren 10 ciudades fijas
  (`download_historical.py:23-34`). *¿Es el conjunto de datos definitivo?*
- **SUPOSICIÓN**: la anomalía nº 1 (características a 0 en el chat) y la nº 2
  (evento `used_ml_prediction`) se registran aquí como anomalías; *¿el negocio
  confirma que el comportamiento actual del chat con estas condiciones es el
  que debe protegerse?*
