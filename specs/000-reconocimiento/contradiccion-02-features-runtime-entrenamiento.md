# Contradicción 02 — Ingeniería de características: runtime vs entrenamiento

Duplicidad de lógica de negocio: la construcción de características del
modelo existe en dos sitios (runtime y script de entrenamiento) y difiere en
semántica y en conjunto de variables. No se decide cuál es la correcta.
Constitución: evidencia y nada corregido.

## 1. Implementaciones implicadas

| # | Implementación | Evidencia | Camino que la usa |
|---|---|---|---|
| 2a | `TemporalFeatureExtractor.extract` (runtime) | `src/infrastructure/ml/feature_extractor.py:24-82` | `/predict` y `/chat` vía DI (`di.py:49-51,76,85`) |
| 2b | `engineer_features` + `build_feature_columns` (entrenamiento) | `scripts/train_model.py:80-103,107-121` | generación de `models/model.pkl` (`train_model.py:158-163`) |

El propio 2a declara la intención de coincidir: "This matches the feature
engineering in scripts/train_model.py" (`feature_extractor.py:21`).

## 2. Comparación paso a paso

| Aspecto | 2a runtime | 2b entrenamiento | ¿Coinciden? |
|---|---|---|---|
| Temporales cíclicos (`hour_sin/cos`, `month_sin/cos`) | `math.sin/cos(2π·h/24)`, `:54-57` | `np.sin/cos(2π·h/24)`, `:95-98` | Sí (misma fórmula) |
| `day_of_week`, `day_of_year`, `is_weekend` | `:58-60` | `:92-94` | Sí |
| Conjunto de variables de lag | 8 variables (`:63-72`: 6 objetivo + `wind_direction_10m`, `dew_point_2m`) | 6 variables (`:36-43`, `TARGET_VARIABLES`; `NUMERIC_FEATURES` en `:48` se define y **no se usa**) | **No** (2 extra en runtime, luego descartadas) |
| Valor del lag h | **valor actual** para todos los h (`:74-77`) | **valor de h filas antes** (`shift(h)`, `:100`) | **No** (semántica distinta) |
| Marca temporal | `timestamp` de la petición (UTC, `predict/handler.py:75`; `created_at` UTC, `ask_agent/handler.py:159`) | columna `datetime` del CSV (verificada en UTC, arqueología 2026-11-14) | Sí (ambas UTC) |
| Columna `city` | pasa el nombre (`:81`) | columna `city` del CSV (`:121`) | Sí |

## 3. Divergencia cuantificada con datos reales

Para una misma ciudad y hora, el "lag h" de 2a (valor actual) y el de 2b
(valor h horas antes) difieren según la variabilidad real del clima. Medido
sobre el CSV completo (263.040 filas, 2026-11-14):

| Variable `temperature_2m` | h=6 | h=12 | h=24 |
|---|---|---|---|
| MAE(valor actual − valor h antes) | **4,00 °C** | **5,48 °C** | **1,86 °C** |
| p90 de la diferencia | 8,30 °C | 10,80 °C | 4,20 °C |
| máxima diferencia | 22,1 °C | 21,7 °C | 19,1 °C |

Es decir: en 9 de cada 10 casos el modelo de entrenamiento recibió un lag
distinto del que recibe el runtime en la misma situación, con diferencias
medias de 2-5 °C. A esto se suma el efecto de C-01 (en el chat, todos los
lags valen 0).

## 4. Cuándo divergen y cuándo coinciden

- **Divergen**: siempre que el tiempo cambie entre t−h y t, que es lo normal
  (solo coincidiría con tiempo perfectamente estable). El caso 24 h diverge
  menos (MAE 1,86 °C) porque la temperatura es cíclica diaria: el valor de
  hace 24 h se parece al actual; probablemente por eso el sistema "funciona
  razonablemente" para el horizonte de 24 h y nadie notó el resto.
- **Coinciden** en los features temporales y en la columna ciudad (misma
  fórmula verificada línea a línea).
- El comentario de 2a ("matches the feature engineering", `:21`) y la
  coherencia de los nombres de columna explican que la duplicidad pasara
  como "sincronizada": los nombres coinciden aunque la semántica no.

## 5. Historia probable

El orden probable es: primero el entrenamiento (2b) con lags reales de
histórico; después, al integrar la inferencia, se reescribió la ingeniería
"en vivo" donde solo hay presente, no pasado: sin histórico en runtime, el
valor actual se reutiliza como sustituto del lag (`:62` lo dice literalmente:
"Lag features: current conditions used as lag for each horizon"). El
comentario de coincidencia (`:21`) se redactó para señalar el intento de
paridad de nombres, no de semántica. `NUMERIC_FEATURES` (`:48`) es el vestigio
de una versión que contemplaba 8 variables numéricas, abandonada al fijar los
targets en 6.

## Pregunta de negocio asociada

¿Es aceptable que la inferencia use el valor actual como "lag" de todos los
horizontes, o debe alinearse con la semántica del entrenamiento (lo que
exige reentrenar o llevar histórico a runtime)? Responsable: sin identificar.
