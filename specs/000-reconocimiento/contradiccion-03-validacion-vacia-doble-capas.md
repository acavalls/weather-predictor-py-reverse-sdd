# Contradicción 03 — Validación de entrada vacía en dos capas con criterios distintos

Duplicidad de lógica de negocio: "rechazar una pregunta vacía" está
implementado dos veces con criterios y resultados diferentes. No se decide
cuál es el correcto.

## 1. Implementaciones implicadas

| # | Implementación | Evidencia | Camino que la usa |
|---|---|---|---|
| 3a | Validación de esquema Pydantic: `min_length=1` sobre el campo `query` | `src/infrastructure/http/routes/chat.py:27` | Toda petición `POST /chat` (FastAPI, antes del caso de uso) |
| 3b | Validación de dominio: `query_text.strip()` no vacío en `AskAgentCommand.__post_init__` | `src/application/ask_agent/command.py:18-21` | Toda construcción del comando (`chat.py:64`) |

Variante paralela en `/predict`: `PredictRequest.location` con
`min_length=1` (`routes/predict.py:31`) y `PredictCommand` que valida
ciudad no vacía **y** al menos un horizonte
(`application/predict/command.py:18-24`).

## 2. Comparación paso a paso

| Aspecto | 3a Pydantic | 3b dominio | ¿Coinciden? |
|---|---|---|---|
| Criterio de vacío | longitud del string ≥ 1 | `strip()` no vacío | **No**: `"   "` pasa 3a y falla 3b |
| Momento | antes del handler (FastAPI) | al construir el comando | No |
| Código HTTP resultante | 422 (validación de request de FastAPI) | 400 (mapeo `ValueError` en `chat.py:73-78`) | **No** |
| Mensaje al cliente | detalle de validación de Pydantic (lista de errores) | texto de la excepción (`"query_text must not be empty"`) | No |
| ¿Valida solo espacios? | No | Sí | — |

## 3. Divergencia con ejemplos concretos

Misma intención de negocio ("pregunta sin contenido"), dos resultados:

| Entrada | Resultado vía 3a | Resultado vía 3b |
|---|---|---|
| `{"query": ""}` | **422** (falla Pydantic; 3b no llega a ejecutarse) | — |
| `{"query": "   "}` | pasa 3a → **400** con `"query_text must not be empty"` (falla 3b) | — |
| campo `query` ausente | **422** | — |

Divergencia observable: dos códigos HTTP distintos y dos formatos de cuerpo
de error distintos para el mismo defecto de negocio, según **dónde** esté el
vacío (vacío exacto vs espacios).

## 4. Cuándo divergen y cuándo coinciden

- **Divergen** exactamente en la entrada `{"query": "   "}` (y cualquier
  cadena de solo espacios): 3a la acepta, 3b la rechaza con otro código y
  otro formato.
- **Coinciden** en rechazar `""` (aunque con códigos distintos: 422 vs 400
  nunca coincide porque 3b no llega a ejecutarse cuando 3a falla).
- La doble red explica que nadie lo notara: cada capa "funciona" por
  separado; el efecto solo es visible comparando respuestas de ambas capas,
  y no hay tests que fijen el contrato de errores.

## 5. Historia probable

Patrón clásico de capas: el esquema Pydantic se escribió con la validación
"natural" de FastAPI (`min_length=1`, `chat.py:27`); el comando de dominio
se escribió después con validación propia más estricta (`strip()`,
`command.py:18-21`), siguiendo el estilo defensivo del resto de value
objects (`aggregate/__init__.py:39-41` repite la misma comprobación). Nadie
concilió los códigos HTTP resultantes. El mismo patrón se repite en
`/predict` (`predict.py:31` vs `command.py:18-24`).

## Pregunta de negocio asociada

¿Qué contrato de errores debe ver el cliente para una pregunta vacía (un
solo código y un solo formato), y qué se considera "vacío" (¿cadenas de solo
espacios?)? Responsable: sin identificar.
