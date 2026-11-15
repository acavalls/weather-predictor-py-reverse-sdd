"""RN-07, RN-08, RN-09 y anomalías A-04/C-02 — extractor de características.

Fuente: specs/000-reconocimiento/reglas-de-negocio.md (RN-07, RN-08, RN-09)
y contradiccion-02-features-runtime-entrenamiento.md.
Congela el comportamiento del extractor tal cual es: los lags valen el
valor actual (no el de h horas antes), las variables ausentes entran a 0.0
y la dirección del viento/punto de rocío nunca reciben valor real.
"""

from __future__ import annotations

import asyncio
import math

from src.infrastructure.ml.feature_extractor import TemporalFeatureExtractor

from .conftest import CONDICIONES_STD, TS_FEB29, TS_FIJO, TS_FIN_DE_ANIO, TS_SABADO


def extraer(condiciones: dict, ciudad: str = "Madrid", ts=TS_FIJO, horizontes=None):
    if horizontes is None:
        horizontes = [6, 12, 24]
    fs = asyncio.run(
        TemporalFeatureExtractor().extract(
            current_conditions=condiciones, city=ciudad, timestamp=ts, horizons=horizontes
        )
    )
    return fs


class TestRN07AlineacionDeEntradas:
    # RN-07: lo que falta vale 0, lo que sobra se ignora.

    def test_congela_variables_ausentes_valen_cero(self):
        # CONGELA comportamiento actual: sin condiciones, todos los lags a 0.0.
        fs = extraer({})
        d = fs.to_dict()
        assert d["temperature_2m_lag_6"] == 0.0
        assert d["relative_humidity_2m_lag_6"] == 0.0
        assert d["precipitation_lag_24"] == 0.0

    def test_congela_variables_extra_se_ignoran(self):
        # El extractor solo mira sus 8 variables; "otra_clave" no aparece.
        fs = extraer({**CONDICIONES_STD, "otra_clave": 999.0})
        assert "otra_clave" not in fs.to_dict()


class TestRN08LagsValenElTiempoActual:
    # RN-08/A-04/C-02: el lag de h horas recibe el valor ACTUAL, para todo h.

    def test_congela_lag_igual_al_valor_actual_para_todo_horizonte(self):
        fs = extraer(CONDICIONES_STD, horizontes=[6, 12, 24])
        d = fs.to_dict()
        # CONGELA comportamiento actual: 18.5 (valor actual) en lag_6/_12/_24,
        # no el valor de 6/12/24 horas antes como promete el comentario
        # "This matches the feature engineering in scripts/train_model.py".
        assert d["temperature_2m_lag_6"] == 18.5
        assert d["temperature_2m_lag_12"] == 18.5
        assert d["temperature_2m_lag_24"] == 18.5
        assert d["surface_pressure_lag_24"] == 1013.0
        assert d["wind_speed_10m_lag_12"] == 12.3

    def test_congela_divergencia_con_semantica_de_entrenamiento(self):
        # C-02: en el entrenamiento el lag h es el valor de h filas antes
        # (train_model.py:100). Congelamos la semántica de runtime: los tres
        # lags son IDENTICOS entre sí (serían distintos con shift real).
        d = extraer(CONDICIONES_STD).to_dict()
        assert d["temperature_2m_lag_6"] == d["temperature_2m_lag_12"] == d["temperature_2m_lag_24"]


class TestRN09VientoYPuntoRocioACero:
    # RN-09/A-38: con el diccionario de 6 claves de /predict, wind_direction y
    # dew_point nunca reciben valor (y el modelo además ni las consume).

    def test_congela_direccion_y_rocio_a_cero_con_seis_claves(self):
        d = extraer(CONDICIONES_STD).to_dict()
        assert d["wind_direction_10m_lag_6"] == 0.0
        assert d["wind_direction_10m_lag_24"] == 0.0
        assert d["dew_point_2m_lag_6"] == 0.0
        assert d["dew_point_2m_lag_24"] == 0.0


class TestVariablesTemporales:
    # Congela el cálculo temporal: ciclos, día de la semana, frontera de fin
    # de semana (day_of_week >= 5), año bisiesto y fin de año.

    def test_congela_ciclos_para_14h_marzo(self):
        d = extraer(CONDICIONES_STD, ts=TS_FIJO).to_dict()
        assert d["hour_sin"] == math.sin(2 * math.pi * 14 / 24)
        assert d["hour_cos"] == math.cos(2 * math.pi * 14 / 24)
        assert d["month_sin"] == math.sin(2 * math.pi * 3 / 12)
        assert d["month_cos"] == math.cos(2 * math.pi * 3 / 12)
        assert d["day_of_week"] == 4.0
        assert d["day_of_year"] == 75.0
        assert d["is_weekend"] == 0.0

    def test_congela_frontera_fin_de_semana(self):
        # Frontera exacta: day_of_week=4 (viernes) NO es fin de semana;
        # day_of_week=5 (sábado) sí.
        d_vie = extraer(CONDICIONES_STD, ts=TS_FIJO).to_dict()
        d_sab = extraer(CONDICIONES_STD, ts=TS_SABADO).to_dict()
        assert d_vie["is_weekend"] == 0.0
        assert d_sab["is_weekend"] == 1.0
        assert d_sab["day_of_week"] == 5.0

    def test_congela_fin_de_anio(self):
        # 31-12-2023 domingo 23:00 UTC: day_of_year=365, is_weekend=1.
        d = extraer(CONDICIONES_STD, ts=TS_FIN_DE_ANIO).to_dict()
        assert d["day_of_year"] == 365.0
        assert d["day_of_week"] == 6.0
        assert d["is_weekend"] == 1.0
        assert d["hour_sin"] == math.sin(2 * math.pi * 23 / 24)

    def test_congela_febrero_bisiesto(self):
        # 29-02-2024 00:00 UTC: day_of_year=60, hora 0 → sin=0.0, cos=1.0.
        d = extraer(CONDICIONES_STD, ts=TS_FEB29).to_dict()
        assert d["day_of_year"] == 60.0
        assert d["hour_sin"] == 0.0
        assert d["hour_cos"] == 1.0

    def test_congela_hora_cero_negativos_y_extremos(self):
        # Hora 0 y hora 12: valores exactos de los ciclos.
        d0 = extraer({}, ts=TS_FEB29).to_dict()
        assert d0["hour_sin"] == 0.0
        assert d0["hour_cos"] == 1.0
        ts12 = TS_FIJO.replace(hour=12)
        d12 = extraer({}, ts=ts12).to_dict()
        assert d12["hour_sin"] == math.sin(math.pi)  # ≈ 1.22e-16, no exactamente 0
        assert d12["hour_cos"] == -1.0


class TestFormaDelFeatureSet:
    # Congela la forma: 7 temporales + 8 lags por horizonte; ciudad y
    # generated_at viajan tal cual.

    def test_congela_numero_y_orden_de_features(self):
        fs = extraer(CONDICIONES_STD, horizontes=[6, 12, 24])
        nombres = fs.feature_names
        assert len(nombres) == 7 + 8 * 3
        assert nombres[:7] == [
            "hour_sin",
            "hour_cos",
            "month_sin",
            "month_cos",
            "day_of_week",
            "day_of_year",
            "is_weekend",
        ]
        assert nombres[7] == "temperature_2m_lag_6"
        assert nombres[-1] == "precipitation_lag_24"

    def test_congela_horizontes_parciales(self):
        # Con horizontes [6] solo se generan los lags de 6.
        fs = extraer(CONDICIONES_STD, horizontes=[6])
        assert len(fs.features) == 7 + 8
        assert "temperature_2m_lag_12" not in fs.to_dict()

    def test_congela_ciudad_y_generated_at(self):
        fs = extraer(CONDICIONES_STD, ciudad="São Paulo")
        assert fs.city == "São Paulo"  # viaja tal cual, con acento
        assert fs.generated_at is TS_FIJO
