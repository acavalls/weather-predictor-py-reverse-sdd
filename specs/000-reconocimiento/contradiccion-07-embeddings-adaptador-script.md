# Contradicción 07 — Generación de embeddings: adaptador del runtime vs script de ingesta

Duplicidad de lógica: producir vectores de embedding está implementado en el
adaptador del runtime y, por separado, en el script de ingesta. No se decide
cuál es el correcto.

## 1. Implementaciones implicadas

| # | Implementación | Evidencia | Camino que la usa |
|---|---|---|---|
| 7a | `LocalEmbedder` (adaptador, detrás del puerto `Embedder`) | `src/infrastructure/embedding/local_embedder.py:12-56`; puerto en `domain/agent/repository/embedder.py` | `/chat` vía DI (`di.py:60-62`, usado en `ask_agent/handler.py:191`) |
| 7b | `load_model` + `model.encode` directo en el script | `scripts/ingest_knowledge.py:29` (constante), `:357-362` (carga), `:365-380` (encode) | ingesta de la base de conocimiento (`ingest_knowledge.py:main`) |

## 2. Comparación paso a paso

| Aspecto | 7a adaptador | 7b script | ¿Coinciden? |
|---|---|---|---|
| Modelo | `all-MiniLM-L6-v2` (`local_embedder.py:22`) | `all-MiniLM-L6-v2` (`ingest_knowledge.py:29`) | Sí (literal repetido; ver C-10) |
| Carga | perezosa, una vez por proceso (`:26-30`) | una vez por ejecución del script (`:357-362`) | misma librería, distinto ciclo de vida |
| Texto que se embebe | la pregunta del usuario tal cual (`handler.py:191`) | `f"{title}. {content}"` — título + contenido concatenados (`ingest_knowledge.py:369`) | **No** (por diseño: doc vs query, pero la decisión no está documentada en el runtime) |
| Opciones de encode | `convert_to_numpy=True` → `.tolist()` (`:42-43,55-56`) | `show_progress_bar=True` → `.tolist()` (`:369-380`) | salida equivalente |
| ¿Pasa por el puerto `Embedder`? | Sí (implementa `Embedder`) | **No** (reimplementa el trabajo del adaptador) | **No** |
| Dimensionalidad declarada | docstring "384 dims" (`:16,39`) | `EMBEDDING_DIM = 384` (`:30`) | Sí (literal duplicado, ver C-10) |

## 3. Divergencia con ejemplos concretos

Para el **mismo texto**, ambas producen el mismo vector (mismo modelo, misma
librería): no hay divergencia numérica comprobable. La divergencia es
estructural:

| Escenario | Resultado |
|---|---|
| Se cambia `settings.embedder_model` (`settings.py:15`) pensando que gobierna la ingesta | **no cambia nada en la ingesta**: 7b usa su propia constante (`ingest_knowledge.py:29`); el índice `vector(384)` y el runtime quedarían desalineados del nuevo modelo |
| Se actualiza la librería `sentence-transformers` | el runtime y la ingesta se actualizan a la vez (misma venv), pero un embedding regenerado con versión nueva no coincide con los almacenados antes: sin control de versión del modelo de embeddings, la búsqueda RAG degrada silenciosamente |
| Dimensionalidad distinta en el futuro | 7b insertaría en `vector(384)` (`init.sql:20`) y fallaría en insert; 7a buscaría con la dimensión nueva y fallaría en query |

Divergencia medible hoy: ninguna (mismo modelo instalado); el riesgo es de
deriva, no de diferencia actual.

## 4. Cuándo divergen y cuándo coinciden

- **Coinciden** mientras el modelo y su versión sean los mismos en el único
  venv del proyecto — que es el caso desde siempre: por eso nadie lo notó.
- **Divergen** en cuanto se cambia el modelo de embeddings por configuración
  (solo el runtime cambia) o se actualiza la librería (embeddings antiguos
  vs nuevos en la misma tabla). Nada del código detecta esa desalineación:
  no hay metadatos de "modelo de embedding" ni en la tabla ni en el índice
  (`init.sql:16-23`).
- El script además duplica la consulta de similitud de otro modo (ver C-09),
  reforzando el patrón "el script vive al margen del runtime".

## 5. Historia probable

Señales: el script se escribe con psycopg2 síncrono y su propia conexión
(`ingest_knowledge.py:19-20,385-390`), estilo de "job de datos" paralelo a
la aplicación; el adaptador `LocalEmbedder` pertenece a la arquitectura
hexagonal del runtime. Probablemente la ingesta se escribió primero (o en
paralelo, por otra persona/capacidad) y el adaptador se creó después para el
chat, sin unificar: el docstring del script declara el modelo como constante
local (`:29-30`) en lugar de leer `settings.embedder_model` (`settings.py:15`),
que existía para eso.

## Pregunta de negocio asociada

¿Quién es el dueño de la configuración del modelo de embeddings (settings
vs constantes del script) y cómo se controla que la ingesta y el runtime
usen siempre el mismo modelo? Responsable: sin identificar.
