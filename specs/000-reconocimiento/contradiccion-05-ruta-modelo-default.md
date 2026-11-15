# Contradicción 05 — Ruta del modelo por defecto: tres valores distintos

Duplicidad de lógica de configuración: "dónde está el modelo entrenado"
tiene tres valores por defecto distintos repartidos por el código. No se
decide cuál es el correcto.

## 1. Implementaciones implicadas

| # | Sitio | Valor por defecto | Evidencia |
|---|---|---|---|
| 5a | `LocalPredictor.__init__` | `"models/model.pkl"` | `src/infrastructure/ml/local_predictor.py:44` |
| 5b | `AskAgentHandler.__init__` / `PredictHandler.__init__` | `"model.pkl"` (raíz del proyecto) | `src/application/ask_agent/handler.py:52`; `src/application/predict/handler.py:34` |
| 5c | `Settings.model_path` | `"models/model.pkl"` | `src/infrastructure/config/settings.py:14` |

Cableado real: el DI pasa `settings.model_path` a ambos handlers
(`di.py:77,89`), que se lo pasan al predictor en `load_model`
(`ask_agent/handler.py:52,67`; `predict/handler.py:40,47`).

## 2. Comparación paso a paso

| Aspecto | 5a | 5b | 5c |
|---|---|---|---|
| Valor | `models/model.pkl` | `model.pkl` | `models/model.pkl` |
| Capa | infraestructura | aplicación | configuración |
| ¿Se usa en runtime? | solo si nadie pasa `model_path` | solo si nadie pasa `model_path` al handler | **sí** (vía DI es la efectiva) |
| Coherencia interna | — | diverge de 5a y 5c | — |

## 3. Divergencia con ejemplos concretos

La divergencia no se manifiesta con el cableado actual del DI, pero sí en
cualquier uso directo de los handlers (tests de caracterización, scripts,
reutilización fuera de FastAPI):

```python
PredictHandler(weather_provider=..., model_predictor=..., feature_extractor=...)
# → model_path="model.pkl" (5b): FileNotFoundError al predecir,
#   porque el fichero real está en models/model.pkl

LocalPredictor()  # → "models/model.pkl" (5a): funciona desde la raíz
```

Cuantificación: con el valor 5b, la primera predicción falla con
`FileNotFoundError: Model file not found: model.pkl`
(`local_predictor.py:63-64`); con 5a y 5c funciona. Tres módulos, dos
comportamientos.

## 4. Cuándo divergen y cuándo coinciden

- **Coinciden** en producción y demos porque el DI inyecta siempre 5c
  (`di.py:77,89`): los valores por defecto de 5a y 5b nunca se ejercitan.
- **Divergen** en cualquier construcción manual de handlers (el caso que
  los tests de caracterización van a ejercitar primero): el defecto saldrá
  como "el modelo no existe" en vez de "la ruta por defecto está mal".
- La coincidencia forzada por DI explica que nadie lo detectara: el bug
  solo vive en los valores por defecto, que el cableado tapa.

## 5. Historia probable

Señales: el docstring de `LocalPredictor` declara `"models/model.pkl"` como
convención (`local_predictor.py:40-41`), coherente con 5c; los handlers se
escribieron con `model_path: str = "model.pkl"` como parámetro de cómoda
(`ask_agent/handler.py:52`), probablemente copiado de un prototipo anterior
en el que el modelo estaba en la raíz (el docstring del propio predictor
habla de "Wraps the model artifact from scripts/train_model.py",
`local_predictor.py:36-37`). Cuando se introdujo `Settings.model_path`
(5c), los defaults de los handlers quedaron sin revisar.

## Pregunta de negocio asociada

¿Cuál es la ubicación oficial del artefacto del modelo y quién es el dueño
de esa configuración (settings vs defaults de clase)? Responsable: sin
identificar.
