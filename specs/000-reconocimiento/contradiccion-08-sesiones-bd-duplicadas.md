# Contradicción 08 — Sesiones de base de datos: dos fábricas para el mismo propósito

Duplicidad de lógica: obtener sesiones async de PostgreSQL está implementado
dos veces; una de ellas no tiene llamadores. No se decide cuál es la
correcta.

## 1. Implementaciones implicadas

| # | Implementación | Evidencia | Camino que la usa |
|---|---|---|---|
| 8a | `get_engine` / `get_session_factory` / `get_session` en la capa de persistencia | `src/infrastructure/persistence/session.py:11-50` (singletons por globales `:14-15`, docstring "Intended for FastAPI dependency injection" `:42`) | **ninguno en runtime** (solo `get_engine` vía DI: `di.py:53`) |
| 8b | `async_sessionmaker` propio dentro del adaptador RAG | `src/infrastructure/persistence/knowledge_base_adapter.py:27-37` | `/chat` (búsqueda RAG) y la ingesta vía tabla |

Punto de encuentro: el DI pasa el engine de 8a al adaptador de 8b
(`di.py:53-58`), que se construye su propia fábrica de sesiones.

## 2. Comparación paso a paso

| Aspecto | 8a capa de persistencia | 8b adaptador RAG | ¿Coinciden? |
|---|---|---|---|
| Fábrica de sesiones | `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)` (`session.py:24-29`) | `async_sessionmaker(engine, expire_on_commit=False)` (`knowledge_base_adapter.py:34-37`) | Casi: 8b **omite** `class_=AsyncSession` |
| Transacciones | `get_session` entrega sesión sin transacción implícita (`:38-50`) | `session.begin()` por operación (`:42,58`) | **No** (estilos distintos) |
| Ciclo de vida | singleton por proceso (globales `:14-15,20-29`) | uno por instancia del adaptador (singleton vía DI) | equivalente en la práctica |
| Escrituras | no hay escritor que la use | `add_document(s)` con `session.merge` (`:39-67`) | — |
| Lecturas | no hay lector | `search` con SQL crudo y `session.stream` (`:69-82`) | — |

## 3. Divergencia con ejemplos concretos

Hoy no hay divergencia observable en ejecución (8a está muerto). La
divergencia es de contrato para quien escriba código nuevo:

```python
# Camino 8a (intención del docstring): sesión inyectada por request
async def ruta(session: AsyncSession = Depends(get_session)): ...

# Camino 8b (realidad): el adaptador abre y confirma por operación
async with self._session_factory() as session:
    async with session.begin():
        ...
```

Divergencia real pasable: un desarrollador que siga el docstring de 8a
("Intended for FastAPI dependency injection", `session.py:42`) inyectará
sesiones por request, mientras el resto del sistema confirma transacciones
por operación dentro del adaptador: dos modelos transaccionales
incompatibles (sesión larga compartida vs transacción corta por método) con
distintas implicaciones de aislamiento y rollbacks.

## 4. Cuándo divergen y cuándo coinciden

- **Coinciden** en el resultado observable actual: solo 8b ejecuta SQL, y
  su comportamiento (transacción por operación) es el único visible.
- **Divergen** en cuanto se añade la segunda tabla viva (p. ej. escribir en
  `forecasts`): el nuevo código puede seguir 8a (sesiones por request) o 8b
  (transacción por operación), produciendo dos estilos en el mismo servicio
  con riesgos distintos (una sesión de request abierta durante la llamada
  al LLM de 30 s, `opencode_go_llm.py:36`, mantendría conexiones del pool
  ocupadas).
- No se detectó porque 8a nunca se ejercitó: no hay tests ni segunda tabla
  en uso.

## 5. Historia probable

Señales: 8a es el esqueleto estándar de "persistencia con FastAPI"
(docstring orientado a `Depends`, `:42-50`) y se escribió como parte del
andamiaje inicial; el adaptador RAG (`knowledge_base_adapter.py`) se añadió
después y, por necesidad inmediata, se construyó su propia fábrica a partir
del engine inyectado (`di.py:53-58`), dejando 8a huérfano. La memoria
histórica registra la misma pauta en otros módulos (andamiaje sin consumir:
memoria A6).

## Pregunta de negocio asociada

¿Qué modelo transaccional es el oficial del servicio (sesión por request vs
transacción por operación)? Responsable: sin identificar.
