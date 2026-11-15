# Contradicción 04 — Mapeo de errores HTTP duplicado y asimétrico entre rutas

Duplicidad de lógica: la traducción "excepción → respuesta HTTP" está
escrita dos veces con criterios parcialmente distintos. No se decide cuál es
la correcta.

## 1. Implementaciones implicadas

| # | Implementación | Evidencia | Camino que la usa |
|---|---|---|---|
| 4a | try/except de `/chat`: `NotFoundError`→404, `ValueError`→400, `Exception`→500 con `detail=str(exc)` | `src/infrastructure/http/routes/chat.py:63-84` | `POST /chat` |
| 4b | try/except de `/predict`: `NotFoundError`→404, `ValueError`→400; **sin manejador genérico** | `src/infrastructure/http/routes/predict.py:84-99` | `POST /predict` |

## 2. Comparación paso a paso

| Aspecto | 4a chat | 4b predict | ¿Coinciden? |
|---|---|---|---|
| `NotFoundError` | 404 con `str(exc)` (`:67-72`) | 404 con `str(exc)` (`:90-94`) | Sí |
| `ValueError` | 400 (`:73-78`) | 400 (`:95-99`) | Sí |
| Cualquier otra excepción | 500 con el **texto de la excepción** en `detail` (`:79-84`) | 500 por defecto de FastAPI ("Internal Server Error" genérico) | **No** |
| Logging del error | `logger.error`/`logger.exception` con contexto (`:68,74,80`) | ninguno | **No** |
| Estructura del código | copiada — mismos bloques try/except con mismos mensajes | copiada | misma forma, distinto contenido |

## 3. Divergencia con ejemplos concretos

Mismo tipo de fallo interno, resultados distintos según el endpoint:

| Fallo (misma causa raíz) | `/chat` | `/predict` |
|---|---|---|
| PostgreSQL caído durante la búsqueda RAG | **500** con `detail` = texto de la excepción de SQLAlchemy (incluye detalles de la BD) | (no aplica: `/predict` no consulta BD) |
| Error no previsto en el use case (p. ej. `FileNotFoundError` por `model.pkl` ausente, `local_predictor.py:63-64`) | **500** con `detail = "Model file not found: models/model.pkl"` | **500** con cuerpo `"Internal Server Error"` (sin detalle) y **sin entrada en el log de la aplicación** |
| Timeout del LLM | 500 con texto de httpx | (no aplica) |

Cuantificación: ante el mismo fallo de modelo ausente, un cliente de `/chat`
recibe la ruta del fichero y el tipo de error; uno de `/predict` recibe un
mensaje genérico. El diagnóstico tampoco es equivalente: en `/predict` la
traza solo aparece en el log por defecto de uvicorn, no via
`logger.exception`.

## 4. Cuándo divergen y cuándo coinciden

- **Coinciden** en los dos casos felices del mapeo (404 y 400), que son los
  que se ven en demos normales (ciudad inexistente, cuerpo inválido).
- **Divergen** en cualquier error no previsto, que es exactamente el caso
  que nunca se prueba manualmente. La asimetría es invisible hasta que algo
  falla de verdad.
- Nota: la divergencia 4b es además un hueco de observabilidad (sin log
  propio), no solo de contrato.

## 5. Historia probable

Señales: 4b (`predict.py`) se presenta a sí mismo como "debug endpoint"
(`predict.py:1`) y su mapeo es una copia reducida del de chat — probablemente
se copió de `chat.py` cuando se añadió el endpoint, recortando el
manejador genérico (y el logging) al considerarlo endpoint de depuración. No
hay comentario que documente la decisión de omitir el 500 con detalle. El
estilo (mismas cadenas de `raise ... from exc`) confirma el origen por
copia.

## Pregunta de negocio asociada

¿Debe haber un único contrato de errores para ambos endpoints (y debe el
detalle interno exponerse al cliente en alguno)? Responsable: sin
identificar.
