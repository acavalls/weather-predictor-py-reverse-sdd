"""RN-05, RN-06, RN-07, RN-12 y anomalías A-02, A-03, A-43 — predictor local.

Fuente: reglas-de-negocio.md (RN-05, RN-06, RN-07, RN-12), contradicciones
C-01/C-02/C-05 y registro-de-anomalias.md (A-02, A-03, A-43).
Valores transcritos de la ejecución real contra `models/model.pkl`
(md5 truncado b59e0918) el 2026-11-14.
"""

from __future__ import annotations

import asyncio
import hashlib

import numpy as np
import pytest

from src.domain.ml.value_objects import Feature, FeatureSet, PredictionResult
from src.infrastructure.ml.local_predictor import LocalPredictor

from .conftest import CONDICIONES_STD, MODEL_PATH, TS_FIJO, predictor_cargado


def construir_feature_set(ciudad: str, condiciones: dict, horizontes=None):
    from src.infrastructure.ml.feature_extractor import TemporalFeatureExtractor

    if horizontes is None:
        horizontes = [6, 12, 24]
    return asyncio.run(TemporalFeatureExtractor().extract(condiciones, ciudad, TS_FIJO, horizontes))


def predecir(ciudad: str, condiciones: dict, horizontes=None):
    predictor, meta = predictor_cargado()
    fs = construir_feature_set(ciudad, condiciones, horizontes)
    return asyncio.run(predictor.predict(meta, fs, horizontes or [6, 12, 24]))


class TestMetadatosDelModeloReal:
    # Congela la forma del artefacto cargado (testigo DATOS del registro).

    def test_congela_horizontes_entrenados(self):
        _, meta = predictor_cargado()
        assert tuple(meta.horizons) == (6, 12, 24, 48, 72, 168)

    def test_congela_columnas_de_features(self):
        _, meta = predictor_cargado()
        assert len(meta.feature_columns) == 44
        assert meta.feature_columns[0] == "hour_sin"
        assert meta.feature_columns[-1] == "city"
        # CONGELA comportamiento actual (A-38): el modelo NO consume
        # dew_point ni wind_direction aunque el extractor los calcule.
        assert not any("dew_point" in c for c in meta.feature_columns)
        assert not any("wind_direction" in c for c in meta.feature_columns)

    def test_congela_columnas_de_targets(self):
        _, meta = predictor_cargado()
        assert len(meta.target_columns) == 36
        assert meta.target_columns[0] == "temperature_2m_target_6"
        assert meta.target_columns[-1] == "precipitation_target_168"

    def test_congela_scores_publicados(self):
        _, meta = predictor_cargado()
        # CONGELA comportamiento actual (A-01): 0.3713 es R² ENTRE CIUDADES
        # (test = solo São Paulo + Tokyo), no fiabilidad del servicio.
        assert meta.test_score == 0.3712878051017324
        assert meta.train_score == 0.5431063937097727

    def test_congela_version_md5_y_mtime(self):
        # RN-12/A-22: versión = MD5 truncado del binario; fecha = mtime.
        predictor, _ = predictor_cargado()
        version_md5 = hashlib.md5(MODEL_PATH.read_bytes()).hexdigest()[:8]
        version = asyncio.run(predictor.get_model_version())
        assert version.version == version_md5
        assert version.version == "b59e0918"
        assert version.trained_at.timestamp() == pytest.approx(MODEL_PATH.stat().st_mtime)
        assert version.horizons == (6, 12, 24, 48, 72, 168)


class TestRN05HorizontesQueElModeloConoce:
    # RN-05: los horizontes no entrenados se descartan sin aviso; si no
    # queda ninguno, ValueError con el mensaje técnico interno.

    def test_congela_horizonte_desconocido_se_descarta_sin_aviso(self):
        # CONGELA comportamiento actual: [6, 999] → solo se devuelve 6.
        resultado = predecir("Madrid", CONDICIONES_STD, [6, 999])
        assert list(resultado.predictions.keys()) == [6]

    def test_congela_sin_horizontes_validos_value_error(self):
        with pytest.raises(ValueError) as exc:
            predecir("Madrid", CONDICIONES_STD, [999])
        assert str(exc.value) == "Prediction result must contain at least one prediction"

    def test_congela_horizontes_no_solicitados_no_aparecen(self):
        resultado = predecir("Madrid", CONDICIONES_STD, [12])
        assert list(resultado.predictions.keys()) == [12]


class TestRN06NombresPorConvencion:
    # RN-06: parseo {variable}_target_{horizonte} con rsplit.

    def test_congela_parseo_de_nombres(self):
        raw = np.array([[1.5, 2.5, 3.5, 4.5]])
        targets = ["temperature_2m_target_6", "humidity_target_6", "dew_point_2m_target_12", "sin_target"]
        out = LocalPredictor._parse_predictions(raw, targets, [6, 12])
        # CONGELA comportamiento actual: "sin_target" se descarta silenciosamente.
        assert out == {6: {"temperature_2m": 1.5, "humidity": 2.5}, 12: {"dew_point_2m": 3.5}}

    def test_congela_filtro_de_horizonte_no_pedido(self):
        raw = np.array([[1.0, 2.0]])
        targets = ["temperature_2m_target_6", "temperature_2m_target_12"]
        out = LocalPredictor._parse_predictions(raw, targets, [6])
        assert out == {6: {"temperature_2m": 1.0}}  # 12 existe en el modelo pero no se pidió

    def test_congela_array_1d_usa_todo(self):
        raw = np.array([7.5])
        out = LocalPredictor._parse_predictions(raw, ["temperature_2m_target_6"], [6])
        assert out == {6: {"temperature_2m": 7.5}}


class TestRN07AlineacionDeCaracteristicas:
    # RN-07: ausentes → 0.0, extra → descartadas, ciudad viaja como texto.

    def test_congela_alineacion(self):
        features = {"temperature_2m_lag_6": 18.5, "columna_extra": 999.0}
        columnas = ["temperature_2m_lag_6", "precipitation_lag_6", "city"]
        alineado = LocalPredictor._align_features(features, columnas, "São Paulo")
        # CONGELA comportamiento actual: faltan → 0.0; sobra → fuera; ciudad → texto.
        assert alineado == {
            "temperature_2m_lag_6": 18.5,
            "precipitation_lag_6": 0.0,
            "city": "São Paulo",
        }

    def test_congela_conversion_a_float(self):
        alineado = LocalPredictor._align_features({"x": "3"}, ["x"], "Madrid")
        assert alineado["x"] == 3.0 and isinstance(alineado["x"], float)


class TestA02CiudadesFueraDelOneHot:
    # CONGELA comportamiento actual (A-02): Tokyo y São Paulo no están en el
    # OneHot (solo 8 categorías) → se codifican a ceros y sus predicciones
    # difieren de las de una ciudad conocida con las MISMAS condiciones.
    # Transcrito de la ejecución real 2026-11-14 (TS_FIJO, CONDICIONES_STD).

    PRED_MADRID = {
        6: {
            "temperature_2m": 18.178030264044768,
            "relative_humidity_2m": 60.13257982269474,
            "surface_pressure": 929.9966631445844,
            "wind_speed_10m": 9.318405175006339,
            "cloud_cover": 47.0890500894344,
            "precipitation": 0.0019082849948656555,
        },
        12: {
            "temperature_2m": 18.682574870184492,
            "relative_humidity_2m": 62.9536194010657,
            "surface_pressure": 980.5927388069898,
            "wind_speed_10m": 10.498974004230217,
            "cloud_cover": 52.373835794547766,
            "precipitation": 0.022144072633012983,
        },
        24: {
            "temperature_2m": 14.805647727026313,
            "relative_humidity_2m": 55.07452711732383,
            "surface_pressure": 971.0743801325552,
            "wind_speed_10m": 8.956829409294269,
            "cloud_cover": 47.53461701388228,
            "precipitation": 0.034368230428695266,
        },
    }

    def test_congela_madrid_ciudad_conocida(self):
        assert predecir("Madrid", CONDICIONES_STD).predictions == self.PRED_MADRID

    def test_congela_tokyo_codificado_a_ceros(self):
        resultado = predecir("Tokyo", CONDICIONES_STD)
        # Difiere de Madrid solo en humidity a 6 h; el resto es IDÉNTICO:
        # el OneHot a ceros apenas mueve el modelo.
        assert resultado.predictions[6]["relative_humidity_2m"] == 60.92908951903441
        assert resultado.predictions[6]["relative_humidity_2m"] != self.PRED_MADRID[6]["relative_humidity_2m"]
        assert resultado.predictions[6]["temperature_2m"] == self.PRED_MADRID[6]["temperature_2m"]
        assert resultado.predictions[12] == self.PRED_MADRID[12]
        assert resultado.predictions[24] == self.PRED_MADRID[24]

    def test_congela_sao_paulo_codificado_a_ceros(self):
        resultado = predecir("São Paulo", CONDICIONES_STD)
        assert resultado.predictions[6]["relative_humidity_2m"] == 60.92908951903441
        assert resultado.predictions[12] == self.PRED_MADRID[12]

    def test_congela_ciudad_inexistente_en_cualquier_categoria(self):
        # "Atlantis" no está en ninguna categoría del OneHot: mismo destino
        # que Tokyo/São Paulo (codificación a ceros).
        resultado = predecir("Atlantis", CONDICIONES_STD)
        assert resultado.predictions[6]["relative_humidity_2m"] == 60.92908951903441


class TestA03ChatPrediceConCeros:
    # CONGELA comportamiento actual (A-03/C-01): pasando al extractor las
    # claves que produce CurrentWeather.to_features() (ruta del chat), TODOS
    # los lags entran a 0.0 y las predicciones divergen de la ruta /predict.
    # Transcrito de la ejecución real 2026-11-14.

    def test_congela_claves_de_to_features_no_llegan_al_extractor(self):
        from src.domain.weather.repository import CurrentWeather
        from src.domain.weather.value_objects import (
            CloudCover,
            Humidity,
            Location,
            Precipitation,
            Pressure,
            Temperature,
            WindSpeed,
        )

        cw = CurrentWeather(
            location=Location(40.4168, -3.7038, "Madrid"),
            temperature=Temperature(18.5),
            humidity=Humidity(62.0),
            pressure=Pressure(1013.0),
            wind_speed=WindSpeed(12.3),
            cloud_cover=CloudCover(40.0),
            precipitation=Precipitation(0.0),
        )
        fs = construir_feature_set("Madrid", cw.to_features())
        assert fs.to_dict()["temperature_2m_lag_6"] == 0.0  # la clave real era "temperature"

    def test_congela_divergencia_chat_vs_predict(self):
        from src.domain.weather.repository import CurrentWeather
        from src.domain.weather.value_objects import (
            CloudCover,
            Humidity,
            Location,
            Precipitation,
            Pressure,
            Temperature,
            WindSpeed,
        )

        cw = CurrentWeather(
            location=Location(40.4168, -3.7038, "Madrid"),
            temperature=Temperature(18.5),
            humidity=Humidity(62.0),
            pressure=Pressure(1013.0),
            wind_speed=WindSpeed(12.3),
            cloud_cover=CloudCover(40.0),
            precipitation=Precipitation(0.0),
        )
        resultado_chat = predecir("Madrid", cw.to_features())
        # CONGELA: con las mismas condiciones reales, la ruta del chat
        # predice 5.96 °C a 6 h frente a 18.18 °C de la ruta /predict.
        assert resultado_chat.predictions[6]["temperature_2m"] == 5.962243504387119
        assert resultado_chat.predictions[6]["relative_humidity_2m"] == 18.784850170987944
        assert resultado_chat.predictions[6]["surface_pressure"] == 787.1886321698162
        assert resultado_chat.predictions[12]["temperature_2m"] == 1.8996718078228674
        assert resultado_chat.predictions[24]["temperature_2m"] == 2.681676703941512
        # Divergencias respecto a /predict con las mismas condiciones:
        pred_madrid = TestA02CiudadesFueraDelOneHot.PRED_MADRID
        assert resultado_chat.predictions[6]["temperature_2m"] != pred_madrid[6]["temperature_2m"]


class TestA43PrediccionDependeDeLosHorizontesPedidos:
    # CONGELA comportamiento actual (A-43, hallazgo de la caracterización):
    # pedir menos horizontes cambia la predicción de los que se conservan,
    # porque los lags de los horizontes no pedidos entran a 0.0 en el
    # alineado (RN-07) en lugar de valer el tiempo actual.

    def test_congela_h6_con_solo_horizonte_6(self):
        resultado = predecir("Madrid", CONDICIONES_STD, [6])
        # Con [6]: lag_12/lag_24 → 0.0 → temperatura a 6 h = 4.25 °C.
        assert resultado.predictions[6]["temperature_2m"] == 4.250787940828976

    def test_congela_h6_con_tres_horizontes(self):
        resultado = predecir("Madrid", CONDICIONES_STD, [6, 12, 24])
        # Con [6,12,24]: lag_12/lag_24 = valor actual → temperatura a 6 h = 18.18 °C.
        assert resultado.predictions[6]["temperature_2m"] == 18.178030264044768


class TestCicloDeVidaDelPredictor:
    # Congela los errores de uso del adaptador.

    def test_congela_predecir_sin_cargar(self):
        predictor = LocalPredictor()
        fs = FeatureSet(features=[Feature("hour_sin", 0.0)], city="Madrid", generated_at=TS_FIJO)
        with pytest.raises(ValueError) as exc:
            asyncio.run(predictor.predict(None, fs, [6]))
        assert str(exc.value) == "Model not loaded. Call load_model() first."

    def test_congela_fichero_inexistente(self):
        predictor = LocalPredictor(default_model_path="models/no_existe.pkl")
        with pytest.raises(FileNotFoundError) as exc:
            asyncio.run(predictor.load_model())
        assert str(exc.value) == "Model file not found: models/no_existe.pkl"

    def test_congela_get_model_version_sin_cargar_pipeline(self):
        predictor = LocalPredictor()
        version = asyncio.run(predictor.get_model_version())
        assert version.version == "b59e0918"


class TestPrediccionResultInvariantes:
    # Congela la invariante del resultado y los getters muertos (A-23).

    def test_congela_resultado_vacio_rechazado(self):
        _, meta = predictor_cargado()
        from datetime import datetime, timezone

        with pytest.raises(ValueError) as exc:
            PredictionResult(
                model_version=meta.version,
                predictions={},
                predicted_at=datetime.now(timezone.utc),
            )
        assert str(exc.value) == "Prediction result must contain at least one prediction"

    def test_congela_getters(self):
        _, meta = predictor_cargado()
        from datetime import datetime, timezone

        resultado = PredictionResult(
            model_version=meta.version,
            predictions={
                6: {
                    "temperature_2m": 18.5,
                    "relative_humidity_2m": 62.0,
                    "surface_pressure": 1013.0,
                    "wind_speed_10m": 12.3,
                    "cloud_cover": 40.0,
                    "precipitation": 0.0,
                }
            },
            predicted_at=datetime.now(timezone.utc),
        )
        assert resultado.get_temperature(6) == 18.5
        assert resultado.get_humidity(6) == 62.0
        assert resultado.get_pressure(6) == 1013.0
        assert resultado.get_wind_speed(6) == 12.3
        assert resultado.get_cloud_cover(6) == 40.0
        assert resultado.get_precipitation(6) == 0.0
