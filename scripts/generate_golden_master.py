"""Generador del golden master del flujo central de negocio (/predict).

Ejecuta el caso de uso de predicción (PredictHandler) con un proveedor
meteorológico fijo y el modelo real `models/model.pkl`, y escribe la
salida COMPLETA (todos los decimales, claves ordenadas) en
`tests/golden_master/master.json`.

Uso:
    PYTHONPATH=. venv/bin/python scripts/generate_golden_master.py

REGLA (constitución, Principio I): el master solo se regenera con una
decisión de negocio documentada (ver LEEME junto al master). Si un test
del master falla, primero se investiga qué cambió; nunca se regenera para
"hacer que pase".

Determinismo:
- El reloj del handler se congela (no se toca código de producción).
- Las condiciones meteorológicas son fijas por caso (sin Open-Meteo).
- El modelo es el artefacto real; su versión (md5) viaja en el master.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import unittest.mock
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.application.predict.command import PredictCommand
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
from src.infrastructure.ml.feature_extractor import TemporalFeatureExtractor
from src.infrastructure.ml.local_predictor import LocalPredictor

MODELO = Path("models/model.pkl")
MASTER = Path("tests/golden_master/master.json")

# Condiciones estándar (claves Open-Meteo, las de la ruta /predict).
CONDICIONES_STD = {
    "temperature_2m": 18.5,
    "relative_humidity_2m": 62.0,
    "surface_pressure": 1013.0,
    "wind_speed_10m": 12.3,
    "cloud_cover": 40.0,
    "precipitation": 0.0,
}

# Condiciones con las claves que produce CurrentWeather.to_features()
# (las que recibe el extractor en la ruta del chat → todos los lags a 0.0,
# anomalía A-03).
CONDICIONES_CHAT = {
    "temperature": 18.5,
    "humidity": 62.0,
    "pressure": 1013.0,
    "wind_speed": 12.3,
    "cloud_cover": 40.0,
    "precipitation": 0.0,
}

# Condiciones en los extremos físicos aceptados (RN-04).
CONDICIONES_EXTREMAS = {
    "temperature_2m": -40.0,
    "relative_humidity_2m": 0.0,
    "surface_pressure": 870.0,
    "wind_speed_10m": 0.0,
    "cloud_cover": 100.0,
    "precipitation": 0.0,
}

TS_FIJO = datetime(2024, 3, 15, 14, 0, 0, tzinfo=timezone.utc)
TS_SABADO = datetime(2024, 3, 16, 14, 0, 0, tzinfo=timezone.utc)
TS_FEB29 = datetime(2024, 2, 29, 0, 0, 0, tzinfo=timezone.utc)
TS_FIN_DE_ANIO = datetime(2023, 12, 31, 23, 0, 0, tzinfo=timezone.utc)


class _RelojCongelado:
    """Sustituto de datetime para el handler (no se toca código de producción)."""

    @staticmethod
    def now(tz: Optional[timezone] = None) -> datetime:
        return TS_FIJO if tz is None else TS_FIJO


class _ProveedorFijo:
    """WeatherProvider de mentira: devuelve siempre las mismas condiciones."""

    def __init__(self, ciudad: str, condiciones: Dict[str, float], latitud: float, longitud: float):
        self._ciudad = ciudad
        self._condiciones = condiciones
        self._lat = latitud
        self._lon = longitud

    async def geocode(self, city_name: str) -> Location:
        return Location(self._lat, self._lon, self._ciudad)

    async def get_current_weather(self, location: Location) -> CurrentWeather:
        return CurrentWeather(
            location=location,
            temperature=Temperature(self._condiciones.get("temperature_2m", 0.0)),
            humidity=Humidity(self._condiciones.get("relative_humidity_2m", 0.0)),
            pressure=Pressure(self._condiciones.get("surface_pressure", 1013.0)),
            wind_speed=WindSpeed(self._condiciones.get("wind_speed_10m", 0.0)),
            cloud_cover=CloudCover(self._condiciones.get("cloud_cover", 0.0)),
            precipitation=Precipitation(self._condiciones.get("precipitation", 0.0)),
        )

    async def get_historical_weather(self, location, start_date, end_date):
        raise NotImplementedError("no usado en el flujo central")


# Juego fijo de 12 casos: ciudades dentro/fuera del OneHot, rutas de claves
# chat vs /predict, fronteras de horizontes, fin de semana, año bisiesto,
# fin de año y extremos físicos.
CASOS = [
    # id, ciudad, condiciones, lat, lon, horizontes, timestamp
    ("madrid_estandar", "Madrid", CONDICIONES_STD, 40.4168, -3.7038, [6, 12, 24], TS_FIJO),
    ("madrid_chat_ceros", "Madrid", CONDICIONES_CHAT, 40.4168, -3.7038, [6, 12, 24], TS_FIJO),
    ("tokyo_fuera_onehot", "Tokyo", CONDICIONES_STD, 35.6762, 139.6503, [6, 12, 24], TS_FIJO),
    ("sao_paulo_fuera_onehot", "São Paulo", CONDICIONES_STD, -23.5505, -46.6333, [6, 12, 24], TS_FIJO),
    ("berlin_conocida", "Berlin", CONDICIONES_STD, 52.52, 13.405, [6, 12, 24], TS_FIJO),
    ("atlantis_inexistente", "Atlantis", CONDICIONES_STD, 0.0, 0.0, [6, 12, 24], TS_FIJO),
    ("madrid_sabado", "Madrid", CONDICIONES_STD, 40.4168, -3.7038, [6, 12, 24], TS_SABADO),
    ("madrid_solo_h6", "Madrid", CONDICIONES_STD, 40.4168, -3.7038, [6], TS_FIJO),
    ("madrid_horizontes_mixtos", "Madrid", CONDICIONES_STD, 40.4168, -3.7038, [6, 999], TS_FIJO),
    ("madrid_extremos_fisicos", "Madrid", CONDICIONES_EXTREMAS, 40.4168, -3.7038, [6, 12, 24], TS_FIJO),
    ("madrid_feb29_bisiesto", "Madrid", CONDICIONES_STD, 40.4168, -3.7038, [6, 12, 24], TS_FEB29),
    ("madrid_fin_de_anio", "Madrid", CONDICIONES_STD, 40.4168, -3.7038, [6, 12, 24], TS_FIN_DE_ANIO),
]


def _current_weather_de(condiciones: Dict[str, float], ciudad: str, lat: float, lon: float) -> CurrentWeather:
    return CurrentWeather(
        location=Location(lat, lon, ciudad),
        temperature=Temperature(condiciones.get("temperature_2m", 0.0)),
        humidity=Humidity(condiciones.get("relative_humidity_2m", 0.0)),
        pressure=Pressure(condiciones.get("surface_pressure", 1013.0)),
        wind_speed=WindSpeed(condiciones.get("wind_speed_10m", 0.0)),
        cloud_cover=CloudCover(condiciones.get("cloud_cover", 0.0)),
        precipitation=Precipitation(condiciones.get("precipitation", 0.0)),
    )


def ejecutar_caso(
    id_caso: str, ciudad: str, condiciones: Dict[str, float], lat: float, lon: float, horizontes: list, ts: datetime
) -> Dict[str, Any]:
    """Ejecuta el flujo central (PredictHandler) con reloj congelado."""
    proveedor = _ProveedorFijo(ciudad, condiciones, lat, lon)
    predictor = LocalPredictor()
    asyncio.run(predictor.load_model())
    handler = PredictHandler(
        weather_provider=proveedor,
        model_predictor=predictor,
        feature_extractor=TemporalFeatureExtractor(),
        # C-05: el default del handler es "model.pkl" (otra ruta que la del
        # predictor); aquí se pasa la ruta real del artefacto.
        model_path="models/model.pkl",
    )
    comando = PredictCommand(city=ciudad, horizons=list(horizontes))
    with unittest.mock.patch("src.application.predict.handler.datetime", _RelojCongelado):
        resultado = asyncio.run(handler.execute(comando))
    return {
        "city": resultado.city,
        "location_name": resultado.location_name,
        "latitude": resultado.latitude,
        "longitude": resultado.longitude,
        "model_version": resultado.model_version,
        "predictions": resultado.predictions,
        "_meta_caso": {"id": id_caso, "horizons": horizontes, "timestamp": ts.isoformat()},
    }


def generar_master() -> Dict[str, Any]:
    casos: Dict[str, Any] = {}
    for id_caso, ciudad, condiciones, lat, lon, horizontes, ts in CASOS:
        casos[id_caso] = ejecutar_caso(id_caso, ciudad, condiciones, lat, lon, horizontes, ts)
    return {
        "_meta": {
            "descripcion": "Golden master del flujo central (/predict) del sistema tal cual es",
            "modelo_md5": hashlib.md5(MODELO.read_bytes()).hexdigest()[:8],
            "reloj": "congelado (ver scripts/generate_golden_master.py)",
            "excluido": "predicted_at (depende del reloj real del predictor)",
        },
        "casos": casos,
    }


def main() -> None:
    master = generar_master()
    MASTER.parent.mkdir(parents=True, exist_ok=True)
    MASTER.write_text(
        json.dumps(master, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Golden master escrito en {MASTER} con {len(master['casos'])} casos.")


if __name__ == "__main__":
    if "--check" not in sys.argv:
        main()
