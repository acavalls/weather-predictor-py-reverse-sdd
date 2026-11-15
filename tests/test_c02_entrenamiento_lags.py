"""C-02 (lado entrenamiento) y RN-14/RN-16 — utilidades puras del script.

Fuente: contradiccion-02-features-runtime-entrenamiento.md y
reglas-de-negocio.md (RN-14, RN-16, RN-17).
Congela la semántica de entrenamiento: los lags valen h FILAS antes y los
targets h filas después dentro de cada ciudad, con descarte de colas.
"""

from __future__ import annotations

import pandas as pd

from scripts.train_model import (
    TARGET_VARIABLES,
    build_feature_columns,
    build_target_columns,
    engineer_features,
    prepare_targets,
)


def _df_ciudades(filas_por_ciudad: int = 20) -> pd.DataFrame:
    # Dos ciudades con valores 0..N-1 en las seis variables objetivo, en el
    # orden del CSV real (bloques por ciudad). Con 20 filas por ciudad y
    # horizonte 6, tras prepare_targets quedan 14 y tras engineer_features 8.
    filas = []
    for ciudad in ["Berlin", "Madrid"]:
        for i in range(filas_por_ciudad):
            filas.append(
                {
                    "datetime": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
                    "city": ciudad,
                    "temperature_2m": float(i),
                    "relative_humidity_2m": 50.0,
                    "surface_pressure": 1013.0,
                    "wind_speed_10m": 10.0,
                    "cloud_cover": 40.0,
                    "precipitation": 0.0,
                }
            )
    return pd.DataFrame(filas)


class TestRN16TargetsYColasPerdidas:
    # RN-16: el objetivo es el valor h filas después; las h últimas filas de
    # cada ciudad no tienen objetivo y se descartan.

    def test_congela_target_es_valor_futuro(self):
        df = prepare_targets(_df_ciudades(), [6])
        berlin = df[df["city"] == "Berlin"].reset_index(drop=True)
        # target_6 de la fila i = valor de la fila i+6.
        assert berlin.loc[0, "temperature_2m_target_6"] == 6.0
        assert berlin.loc[1, "temperature_2m_target_6"] == 7.0

    def test_congela_colas_sin_target_descartadas(self):
        df = prepare_targets(_df_ciudades(), [6])
        # 20 filas por ciudad - 6 colas = 14 filas por ciudad.
        assert len(df) == 28
        assert set(df["city"]) == {"Berlin", "Madrid"}

    def test_congela_con_horizonte_168_solo_queda_la_cabeza(self):
        df = prepare_targets(_df_ciudades(), [168])
        assert len(df) == 0  # ninguna fila tiene 168 filas después


class TestC02LagsFilasAntes:
    # C-02/RN-15: el lag h es el valor de h FILAS antes dentro de la ciudad.

    def test_congela_lag_con_shift_por_ciudad(self):
        # Pipeline real (train_model.py:159-160): primero prepare_targets y
        # DESPUÉS engineer_features: el shift se aplica sobre el marco ya
        # truncado (20→14 filas) y luego el dropna de lags deja 8 por ciudad.
        df = prepare_targets(_df_ciudades(), [6])
        df = engineer_features(df, [6])
        assert len(df) == 16  # 8 filas por ciudad × 2 ciudades
        berlin = df[df["city"] == "Berlin"].reset_index(drop=True)
        # lag_6 de la fila original i = valor de la fila original i-6.
        assert berlin.loc[0, "temperature_2m_lag_6"] == 0.0  # fila original 6
        assert berlin.loc[1, "temperature_2m_lag_6"] == 1.0  # fila original 7

    def test_congela_que_lag_y_target_difieren_para_la_misma_fila(self):
        # Núcleo de C-02: para la misma fila, lag_6 ≠ target_6 (son valores
        # de filas distintas), mientras que el extractor de runtime pondría
        # el valor actual en ambos lados.
        df = prepare_targets(_df_ciudades(), [6])
        df = engineer_features(df, [6])
        madrid = df[df["city"] == "Madrid"].reset_index(drop=True)
        fila = madrid.loc[0]  # fila original 6
        assert fila["temperature_2m_lag_6"] == 0.0  # valor de la fila 0
        assert fila["temperature_2m_target_6"] == 12.0  # valor de la fila 12

    def test_congela_is_weekend_frontera_en_entrenamiento(self):
        # engineer_features marca weekend con day_of_week >= 5 (misma
        # frontera que el extractor de runtime). 20 días desde lunes 01-01.
        df = _df_ciudades()
        df["datetime"] = pd.concat(
            [
                pd.Series([pd.Timestamp("2024-01-01") + pd.Timedelta(days=i) for i in range(20)]),
                pd.Series([pd.Timestamp("2024-01-01") + pd.Timedelta(days=i) for i in range(20)]),
            ],
            ignore_index=True,
        )
        out = engineer_features(df, [6])
        berlin = out[out["city"] == "Berlin"].reset_index(drop=True)
        # Tras el shift(6) sobreviven las filas originales 6..19.
        viernes = berlin.loc[5]  # fila original 11 → viernes 12-01
        sabado = berlin.loc[6]  # fila original 12 → sábado 13-01
        assert viernes["day_of_week"] == 4
        assert viernes["is_weekend"] == 0
        assert sabado["day_of_week"] == 5
        assert sabado["is_weekend"] == 1


class TestColumnasDeContrato:
    # Congela la construcción de columnas: 7 temporales + 6 variables ×
    # horizontes + city (sin dew_point ni wind_direction).

    def test_congela_feature_columns(self):
        cols = build_feature_columns([6, 12, 24])
        assert cols[0:7] == [
            "hour_sin",
            "hour_cos",
            "month_sin",
            "month_cos",
            "day_of_week",
            "day_of_year",
            "is_weekend",
        ]
        assert cols[7] == "temperature_2m_lag_6"
        assert cols[-1] == "city"
        assert len(cols) == 7 + 6 * 3 + 1
        assert not any("dew_point" in c or "wind_direction" in c for c in cols)

    def test_congela_target_columns(self):
        cols = build_target_columns([6])
        assert cols == [f"{v}_target_6" for v in TARGET_VARIABLES]

    def test_congela_variables_objetivo(self):
        # Las 6 variables del esquema (el extractor calcula 8: dos de más).
        assert TARGET_VARIABLES == [
            "temperature_2m",
            "relative_humidity_2m",
            "surface_pressure",
            "wind_speed_10m",
            "cloud_cover",
            "precipitation",
        ]


class TestRN17ConstantesDeEntrenamiento:
    # RN-17: valores fijos de la firma de train_model (semilla 42).

    def test_congela_firma_de_train_model(self):
        import inspect

        from scripts.train_model import train_model

        firma = inspect.signature(train_model)
        assert firma.parameters["test_size"].default == 0.2
        assert firma.parameters["n_estimators"].default == 200
        assert firma.parameters["max_depth"].default == 5
        assert firma.parameters["learning_rate"].default == 0.1
        fuente = inspect.getsource(train_model)
        assert "random_state=42" in fuente
        assert "subsample=0.8" in fuente
