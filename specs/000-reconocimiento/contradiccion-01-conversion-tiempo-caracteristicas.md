# Contradicción 01 — Conversión del tiempo actual en características del modelo

Duplicidad de lógica de negocio: la misma transformación ("tiempo actual →
diccionario de características") está escrita dos veces con convenciones
incompatibles. No se decide cuál es la correcta (pregunta de negocio).
Constitución: evidencia en cada afirmación; nada se corrige.

## 1. Implementaciones implicadas

| # | Implementación | Evidencia | Camino que la usa |
|---|---|---|---|
| 1a | `CurrentWeather.to_features()` — método del objeto de dominio | `src/domain/weather/repository/__init__.py:50-62` (claves `"temperature"`, `"humidity"`, `"pressure"`, `"wind_speed"`, `"cloud_cover"`, `"precipitation"`) | Flujo conversacional: `ask_agent/handler.py:157` |
| 1b | `PredictHandler._weather_to_conditions()` — método estático del handler | `src/application/predict/handler.py:96-115` (claves `"temperature_2m"`, `"relative_humidity_2m"`, `"surface_pressure"`, `"wind_speed_10m"`, `"cloud_cover"`, `"precipitation"`) | Endpoint de predicción: `predict/handler.py:71` |

Consumidor común de ambas salidas: `TemporalFeatureExtractor.extract`
(`src/infrastructure/ml/feature_extractor.py:24-82`), que busca claves de
Open-Meteo (`"temperature_2m"`, …; lista en `:63-72`).

## 2. Comparación paso a paso

| Aspecto | 1a `to_features()` | 1b `_weather_to_conditions()` | ¿Coinciden? |
|---|---|---|---|
| Nombre de clave temperatura | `temperature` | `temperature_2m` | **No** |
| Nombre de clave humedad | `humidity` | `relative_humidity_2m` | **No** |
| Nombre de clave presión | `pressure` | `surface_pressure` | **No** |
| Nombre de clave viento | `wind_speed` | `wind_speed_10m` | **No** |
| Nubes / lluvia | `cloud_cover` / `precipitation` | `cloud_cover` / `precipitation` | Sí |
| Origen del diseño | docstring: "Convert current weather to feature dict for ML model" (`:54-56`) | docstring: "Matches the keys expected by FeatureExtractor (Open-Meteo variable names)" (`:100-102`) | 1b declara explícitamente el contrato; 1a no |

Ambas funciones tienen la misma firma conceptual (objeto de tiempo → dict de
6 valores) y el mismo propósito declarado en sus docstrings ("for ML model"),
pero 1a usa nombres "de negocio" y 1b los nombres de la API de Open-Meteo que
el extractor y el modelo esperan.

## 3. Divergencia cuantificada con datos reales

Experimento (2026-11-14, `models/model.pkl` cargado con el propio runtime):
condición real de Madrid tomada del CSV de producción
(`temperature_2m=7.4, humedad=72, presión=931.3, viento=2.8, nubes=96,
lluvia=0`) y misma marca temporal; única diferencia: qué diccionario recibe
el extractor.

| Horizonte | Temp. vía 1b (predict) | Temp. vía 1a (chat) | Divergencia |
|---|---|---|---|
| 6 h | 8.849 °C | 4.433 °C | **−4.42 °C** |
| 12 h | 7.965 °C | 1.630 °C | **−6.34 °C** |
| 24 h | 6.352 °C | 2.026 °C | **−4.33 °C** |

| Horizonte | Humedad vía 1b | Humedad vía 1a | Divergencia |
|---|---|---|---|
| 6 h | 63.8 % | 21.7 % | **−42.0 pp** |
| 12 h | 75.7 % | 31.7 % | **−44.0 pp** |
| 24 h | 58.7 % | 26.7 % | **−32.1 pp** |

Causa mecánica: con las claves de 1a, el extractor no encuentra ninguna
variable (`feature_extractor.py:76`, `.get(var, 0.0)`) y todos los lags
entran a 0.0; el modelo predice sobre un estado meteorológico vacío.

## 4. Cuándo divergen y cuándo coinciden

- **Divergen**: en cada petición de chat con ciudad detectada
  (`ask_agent/handler.py:157` es el único llamador de 1a). El usuario del
  chat recibe predicciones sistemáticamente distintas a las de `/predict`
  para la misma ciudad y hora.
- **Coinciden**: solo cuando todas las magnitudes valen 0 (ambos caminos
  producen entonces el mismo vector nulo), y en `/predict` (que nunca usa
  1a). La coincidencia aparente en demos con datos neutros explica que no
  se haya detectado: no hay test, y el chat sí devuelve "una predicción"
  plausible, solo que calculada sin condiciones.
- **Por qué nadie lo vio**: el resumen del prompt muestra valores con el
  formato de 1a ("temp=…" con claves de negocio, `handler.py:249-254`), que
  parecen correctos al usuario aunque el modelo haya recibido ceros.

## 5. Historia probable

Señales reconstruidas: 1b vive en el handler y su docstring cita el contrato
del extractor ("Matches the keys expected by FeatureExtractor",
`predict/handler.py:100-102`) — parece posterior al extractor. 1a vive en el
puerto de dominio (`weather/repository`), capa que por arquitectura no debe
conocer nombres de API externa; sus claves "limpias" sugieren que se escribió
primero, con la convención de negocio, antes de que existiera el modelo
Open-Meteo. Cuando se añadió el flujo conversacional (`ask_agent`), se
reutilizó el método de dominio existente (`to_features`) en lugar del
mapeo correcto ya presente en el otro handler. No hay comentario que
documente la decisión ni test que la detecte.

## Pregunta de negocio asociada

¿Qué camino debe definir el contrato de características (los nombres de
Open-Meteo de 1b, o una convención de negocio propia traducida en un solo
sitio)? Responsable: sin identificar (pendiente de entrevista).
