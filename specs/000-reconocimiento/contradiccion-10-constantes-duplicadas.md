# Contradicción 10 — Constantes de negocio duplicadas (modelo de embeddings, dimensión, ciudad por defecto de contexto)

Duplicidad de lógica de configuración de negocio: valores que definen el
contrato entre componentes están escritos en dos o más sitios. No se decide
cuál es el correcto.

## 1. Implementaciones implicadas

| Constante | Sitios | Evidencia |
|---|---|---|
| Modelo de embeddings `all-MiniLM-L6-v2` | `settings.py:15` (`embedder_model`, **no consumido por el adaptador**: `local_embedder.py:22` repite el literal como default); `ingest_knowledge.py:29` (constante propia) | tres sitios, dos mecanismos |
| Dimensión 384 | `knowledge_base.py:17` (`EMBEDDING_DIM`, usa el ORM/índice); `ingest_knowledge.py:30` (`EMBEDDING_DIM`); `init.sql:20` (`vector(384)` en DDL) | tres sitios, incluido DDL |
| Modelo LLM y URL (`mimo-v2.6-flash`, `https://opencode.ai/zen/go/v1`) | `settings.py:11-12`; `opencode_go_llm.py:34-35` (defaults del constructor) | dos sitios |
| Timeout de LLM 30 s | `opencode_go_llm.py:36`; `open_meteo_adapter.py:46` (30.0, otra API pero mismo literal) | dos sitios |
| Lista de variables meteorológicas de Open-Meteo | `open_meteo_adapter.py:102` (parámetro `current`); `predict/handler.py:108-115` (claves del dict); `feature_extractor.py:63-72` (lags); `train_model.py:23-43` (TARGET/NUMERIC_FEATURES); `download_historical.py:39-48` (VARIABLES) | cinco sitios |
| 10 ciudades del dataset | `download_historical.py:22-34` (CITIES); `data/historical_weather.csv` (bloques); `train_model.py` (implícito vía columna) | dos sitios + datos |

## 2. Comparación paso a paso (caso insignia: el modelo de embeddings)

| Aspecto | `settings.embedder_model` | default de `LocalEmbedder` | constante del script |
|---|---|---|---|
| Valor | `all-MiniLM-L6-v2` | `all-MiniLM-L6-v2` | `all-MiniLM-L6-v2` |
| ¿Quién lo lee en runtime? | **nadie** (el DI no lo pasa: `di.py:60-62` instancia `LocalEmbedder()` sin argumentos) | el adaptador | el script |
| Efecto de cambiar el setting | ninguno | — | — |

Caso insignia DDL: `EMBEDDING_DIM = 384` del ORM (`knowledge_base.py:17`) y
`vector(384)` de `init.sql:20` deben coincidir a mano; Alembic no genera el
tipo (la migración solo crea el índice, `alembic/versions/821f93690b12_...py:20-24`).

## 3. Divergencia con ejemplos concretos

| Cambio realizado en un solo sitio | Resultado |
|---|---|
| `settings.embedder_model = "all-mpnet-base-v2"` (768 dims) | el runtime sigue usando MiniLM (el setting es decorativo): sin efecto. Un desarrollador cree haber cambiado el modelo; no cambió nada |
| `EMBEDDING_DIM = 768` solo en el ORM | inserts async de 768 dims contra columna `vector(384)` → error de pgvector en producción |
| nuevo modelo LLM solo en `settings.py` | el DI lo propaga (`di.py:64-69`) → sí cambia; pero scripts o tests que instancien `OpenCodeGoLLM()` sin argumentos seguirán con `mimo-v2.6-flash` |
| nueva variable meteorológica solo en `feature_extractor.py:63-72` | el modelo la descarta silenciosamente (`local_predictor.py:187-192`) o la reclama y entra a 0 (ver C-02) |

## 4. Cuándo divergen y cuándo coinciden

- **Coinciden** mientras nadie toque nada: hoy todos los literales son
  iguales y el DI tapa los settings muertos.
- **Divergen** en cada evolución individual de un sitio: el patrón "cambiar
  el setting no cambia el sistema" (embeddings) y "cambiar el ORM no cambia
  la BD" (dimensión) solo se manifiesta en despliegues o migraciones
  futuras, nunca en la demo.
- Es la causa raíz transversal de C-05 (ruta del modelo), C-06 (horizontes)
  y C-07 (embeddings): el proyecto carece de un único lugar para las
  constantes de contrato.

## 5. Historia probable

Señales: los defaults de constructor duplican los settings
(`opencode_go_llm.py:34-36` replica `settings.py:11-12` con los mismos
valores), y `settings.embedder_model` quedó sin cablear (`di.py:60-62`)
— típico de un sprint de integración donde se creó la configuración
centralizada después de los adaptadores y no se rewiringearon todos los
argumentos. El DDL manual (`init.sql`) y la constante del script
(`EMBEDDING_DIM`) confirman que la BD y la ingesta se montaron al margen de
la capa de configuración.

## Pregunta de negocio asociada

¿Quién es el dueño de las constantes de contrato (modelo de embeddings,
dimensión, variables, ciudades) y debe el negocio validarlas en un único
sitio? Responsable: sin identificar.
