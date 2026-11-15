# Contradicción 09 — Búsqueda vectorial: adaptador async vs consulta del script

Duplicidad de lógica: la búsqueda por similitud coseno sobre `knowledge_base`
está escrita dos veces con convenciones distintas. No se decide cuál es la
correcta.

## 1. Implementaciones implicadas

| # | Implementación | Evidencia | Camino que la usa |
|---|---|---|---|
| 9a | `KnowledgeBaseAdapter.search` (SQL async, parámetro string) | `src/infrastructure/persistence/knowledge_base_adapter.py:69-82` | `/chat` (`ask_agent/handler.py:192`) |
| 9b | consulta de verificación del script de ingesta (psycopg2 síncrono, vector nativo) | `scripts/ingest_knowledge.py:433-457` | autoverificación de la ingesta (`ingest_knowledge.py:main`) |

## 2. Comparación paso a paso

| Aspecto | 9a adaptador | 9b script | ¿Coinciden? |
|---|---|---|---|
| Operador de distancia | `embedding <=> CAST(:embedding AS vector)` (`:74,76`) | `embedding <=> %s::vector` con `register_vector` (`:447-450`) | Sí (mismo operador pgvector) |
| Formato del embedding de entrada | string `"[' + ... + ']"` construido a mano (`:71`) | array nativo de NumPy registrado (`register_vector`, `:389`) | **No** (dos convenciones de binding) |
| Orden | `ORDER BY embedding <=> :embedding` (distancia ASC) (`:76`) | `ORDER BY distance ASC` (`:450-451`) | Sí |
| Límite | `LIMIT :limit`, `top_k=3` desde el handler (`:77`; `handler.py:192`) | `LIMIT 3` fijo (`:452`) | Sí en valor, distinto mecanismo |
| Salida | `1 - distancia AS similarity` → `RetrievedDocument` con validación [0,1] (`:74,95`; `retrieved_document.py:46-49`) | distancia cruda, solo log (`:447-454`) | **No** (una valida rango, la otra no) |
| Driver | SQLAlchemy async (`:80-82`) | psycopg2 síncrono (`:385-390`) | No |

## 3. Divergencia con ejemplos concretos

Misma pregunta, dos salidas distintas por diseño:

| Aspecto | 9a | 9b |
|---|---|---|
| "Will it rain?" sobre la KB real | hasta 3 `RetrievedDocument` con `similarity_score` ∈ [0,1] validado; si el redondeo produce `> 1.0`, **excepción** (400) | imprime distancias crudas en el log, sin validación ni excepción posible |
| binding del embedding | string hand-made (vulnerable a malformación si el texto contiene corchetes/comas anómalas — hoy imposible: son floats) | vector nativo pgvector |

Divergencia cuantificable hoy: ninguna en resultados (mismo operador y
orden sobre los mismos datos devuelven el mismo top-3; verificado por
inspección del SQL, no ejecutado contra BD en esta fase). La divergencia
real es de **contrato**: la vía del runtime valida el rango de similitud y
puede fallar; la del script nunca falla por rango.

## 4. Cuándo divergen y cuándo coinciden

- **Coinciden** en el top-3 devuelto mientras el embedding de consulta sea
  equivalente en ambas convenciones de binding (lo es: floats con `str()`).
- **Divergen** en dos situaciones: (1) validación — una similitud por
  redondeo fuera de [0,1] rompe 9a (registro-riesgos R15) y no afecta a 9b;
  (2) evolución — un cambio de esquema aplicado solo en el runtime (o solo
  en el script) desincroniza las dos consultas sin aviso, porque no hay una
  única definición de "búsqueda".
- Nadie lo notó porque 9b solo se ejecuta tras la ingesta y su salida es un
  log, no una respuesta de negocio.

## 5. Historia probable

Señales: 9b vive en `verify_insertion` (`ingest_knowledge.py:433`), función
de autoverificación del job de ingesta, escrita con el estilo síncrono del
propio script (psycopg2 + `register_vector`, `:19-20,385-390`). 9a se
escribió para el runtime con SQLAlchemy async y el binding string (probable
workaround para evitar `register_vector` en asyncpg). Dos autores/caminos,
mismo operador copiado: el `LIMIT 3` del script (`:452`) replica el
`top_k=3` del handler (`handler.py:192`), señal de copia manual.

## Pregunta de negocio asociada

¿Debe existir una única definición de búsqueda semántica (y qué validación
de similitud es la oficial)? Responsable: sin identificar.
