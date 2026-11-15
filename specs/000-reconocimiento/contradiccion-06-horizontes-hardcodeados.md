# Contradicción 06 — Horizontes de predicción: la misma decisión escrita en seis sitios

Duplicidad de lógica de negocio: la lista de horizontes válidos está
hardcodeada varias veces con dos conjuntos distintos que además se cruzan.
No se decide cuál es el correcto.

## 1. Implementaciones implicadas

| # | Sitio | Valor | Evidencia |
|---|---|---|---|
| 6a | `PredictRequest.horizons` (esquema HTTP) | `[6, 12, 24]` | `src/infrastructure/http/routes/predict.py:32-35` |
| 6b | `PredictCommand.horizons` (comando) | `[6, 12, 24]` | `src/application/predict/command.py:19` |
| 6c | `PredictHandler._default_horizons` | `[6, 12, 24]` | `src/application/predict/handler.py:41` |
| 6d | `AskAgentHandler._gather_weather_context` (dos llamadas) | `[6, 12, 24]` | `src/application/ask_agent/handler.py:160,165` |
| 6e | `train_model.py` (entrenamiento) | `[6, 12, 24, 48, 72, 168]` | `scripts/train_model.py:155` |
| 6f | artefacto `models/model.pkl` (`horizons`) | `[6, 12, 24, 48, 72, 168]` | verificado por joblib (arqueología 2026-11-14); guardado en `train_model.py:236-250` |

## 2. Comparación paso a paso

| Aspecto | 6a-6d (servicio) | 6e-6f (modelo) |
|---|---|---|
| Conjunto | {6, 12, 24} | {6, 12, 24, 48, 72, 168} |
| Papel | filtra qué se pide y qué se devuelve (`local_predictor.py:223-224`) | define qué targets existen (`{var}_target_{h}`) |
| Relación | **subconjunto estricto** del modelo | superconjunto no expuesto |
| Número de sitios con el mismo literal `[6, 12, 24]` | 5 (`predict.py:33`, `command.py:19`, `predict/handler.py:41`, `ask_agent/handler.py:160`, `:165`) | — |

## 3. Divergencia con ejemplos concretos

Misma entrada, resultados distintos según el sitio que decida:

| Petición | Resultado |
|---|---|
| `{"horizons": [48]}` a `/predict` | el modelo **sí tiene** `_target_48` (6f), pero el filtro de runtime compara contra los horizontes **pedidos** y el flujo termina en "Prediction result must contain at least one prediction" → 400 (`ml/value_objects/__init__.py:126`) |
| `{"horizons": []}` | rechazada por el comando (`command.py:21-24`) — tercer criterio distinto |
| horizonte nuevo p. ej. `36` en producción | exige tocar 6a, 6b, 6c, 6d y **reentrenar** (6e/6f); hoy no hay un solo sitio donde "los horizontes de negocio" estén definidos |

Cuantificación de la divergencia: el 50 % de los horizontes entrenados
(3 de 6) es inalcanzable por API; el literal `[6, 12, 24]` está repetido 5
veces.

## 4. Cuándo divergen y cuándo coinciden

- **Coinciden** en el uso normal: las demos y el chat usan siempre los
  valores por defecto `[6, 12, 24]`, que están contenidos en el modelo; el
  filtro nunca descarta nada.
- **Divergen** en cuanto alguien pide un horizonte entrenado pero no
  listado (48/72/168): la divergencia solo se manifiesta con entradas
  fuera del "camino feliz", y no hay test ni documentación de los
  horizontes expuestos.
- Divergencia latente adicional: si el modelo se reentrenara con otros
  horizontes (6e), el servicio (6a-6d) seguiría exponiendo los suyos sin
  aviso: dos fuentes que evolucionan por separado.

## 5. Historia probable

Señales: el entrenamiento se diseñó con ambición (6 horizontes,
`train_model.py:10` en el docstring de uso "--horizon 6 12 24 48 72 168"),
pero el servicio se construyó con tres ("default: [6, 12, 24]" está
documentado en el propio esquema HTTP, `predict.py:34`). El literal repetido
5 veces sin constante compartida sugiere crecimiento por copia al añadir el
flujo conversacional (`ask_agent/handler.py:160,165` duplica el par de
llamadas de `predict/handler.py`). No hay comentario que explique por qué
48/72/168 quedaron fuera del API.

## Pregunta de negocio asociada

¿Qué horizontes son los de negocio (¿solo 6/12/24, o también 48/72/168
entrenados?) y quién mantiene esa lista? Responsable: sin identificar.
