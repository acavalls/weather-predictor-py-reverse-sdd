"""C-01 — el mismo concepto (tiempo actual → características) en dos sitios.

Fuente: specs/000-reconocimiento/contradiccion-01-conversion-tiempo-caracteristicas.md.
Congela CADA implementación por separado con la MISMA entrada
CurrentWeather: producen diccionarios con claves distintas e
incompatibles (origen de A-03).
"""

from __future__ import annotations

from src.application.predict.handler import PredictHandler
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

# Misma entrada para las dos implementaciones.
CW = CurrentWeather(
    location=Location(40.4168, -3.7038, "Madrid"),
    temperature=Temperature(18.5),
    humidity=Humidity(62.0),
    pressure=Pressure(1013.0),
    wind_speed=WindSpeed(12.3),
    cloud_cover=CloudCover(40.0),
    precipitation=Precipitation(0.0),
)


def test_congela_implementacion_a_to_features_ruta_chat():
    # Implementación A: CurrentWeather.to_features()
    # (src/domain/weather/repository/__init__.py:56-63), usada por el chat.
    assert CW.to_features() == {
        "temperature": 18.5,
        "humidity": 62.0,
        "pressure": 1013.0,
        "wind_speed": 12.3,
        "cloud_cover": 40.0,
        "precipitation": 0.0,
    }


def test_congela_implementacion_b_weather_to_conditions_ruta_predict():
    # Implementación B: PredictHandler._weather_to_conditions
    # (src/application/predict/handler.py:108-115), usada por /predict.
    assert PredictHandler._weather_to_conditions(CW) == {
        "temperature_2m": 18.5,
        "relative_humidity_2m": 62.0,
        "surface_pressure": 1013.0,
        "wind_speed_10m": 12.3,
        "cloud_cover": 40.0,
        "precipitation": 0.0,
    }


def test_congela_divergencia_de_claves():
    # Las dos salidas comparten solo 2 claves (cloud_cover, precipitation);
    # las 4 de temperatura/humedad/presión/viento difieren, de modo que la
    # del chat nunca satisface al extractor (A-03).
    claves_a = set(CW.to_features())
    claves_b = set(PredictHandler._weather_to_conditions(CW))
    assert claves_a & claves_b == {"cloud_cover", "precipitation"}
    assert claves_a - claves_b == {"temperature", "humidity", "pressure", "wind_speed"}
    assert claves_b - claves_a == {
        "temperature_2m",
        "relative_humidity_2m",
        "surface_pressure",
        "wind_speed_10m",
    }
