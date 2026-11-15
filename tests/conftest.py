"""Tests de caracterización del sistema weather-agent, tal cual es.

Constitución aplicable (`.specify/memory/constitution.md`):
- El comportamiento actual es sagrado: el valor esperado de cada test es
  EL QUE EL CÓDIGO ACTUAL PRODUCE, transcritos tras ejecutar cada caso
  (2026-11-14). Si un test falla, se corrige el TEST, jamás el código.
- Cada test de anomalía va prefijado "CONGELA comportamiento actual:" y
  remite a su ID del registro de anomalías
  (specs/000-reconocimiento/registro-de-anomalias.md).

Cobertura derivada de los artefactos de reconocimiento: mapa-sistema.md
(criticidad ALTA), reglas-de-negocio.md (RN-01..RN-28),
contradiccion-01..10 y registro-de-anomalias.md (A-01..A-43).

Fuera de la red (IO de red/BD, ver LEEME del golden master y el resumen
final en la documentación): Open-Meteo, LLM OpenCode Go, PostgreSQL
(RAG), scripts de descarga/ingesta y el reentrenamiento completo.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from src.infrastructure.ml.local_predictor import LocalPredictor

MODEL_PATH = Path("models/model.pkl")

# Timestamp fijo de referencia para todos los casos congelados:
# viernes 15-03-2024 14:00 UTC (day_of_week=4, day_of_year=75, is_weekend=0).
TS_FIJO = datetime(2024, 3, 15, 14, 0, 0, tzinfo=timezone.utc)

# Sábado 16-03-2024 14:00 UTC (day_of_week=5 → is_weekend=1).
TS_SABADO = datetime(2024, 3, 16, 14, 0, 0, tzinfo=timezone.utc)

# Domingo 31-12-2023 23:00 UTC (day_of_week=6, day_of_year=365).
TS_FIN_DE_ANIO = datetime(2023, 12, 31, 23, 0, 0, tzinfo=timezone.utc)

# Jueves 29-02-2024 00:00 UTC (año bisiesto, day_of_year=60, is_weekend=0).
TS_FEB29 = datetime(2024, 2, 29, 0, 0, 0, tzinfo=timezone.utc)

# Condiciones meteorológicas estándar con claves Open-Meteo
# (las que espera el extractor; ruta /predict).
CONDICIONES_STD = {
    "temperature_2m": 18.5,
    "relative_humidity_2m": 62.0,
    "surface_pressure": 1013.0,
    "wind_speed_10m": 12.3,
    "cloud_cover": 40.0,
    "precipitation": 0.0,
}


@lru_cache(maxsize=1)
def predictor_cargado() -> tuple[LocalPredictor, object]:
    """Carga el modelo real una sola vez para toda la suite.

    Devuelve (predictor, metadata). El predictor se reutiliza entre tests;
    los métodos async se invocan con asyncio.run desde tests síncronos
    para no depender del loop de pytest-asyncio.
    """
    predictor = LocalPredictor()
    metadata = asyncio.run(predictor.load_model())
    return predictor, metadata
