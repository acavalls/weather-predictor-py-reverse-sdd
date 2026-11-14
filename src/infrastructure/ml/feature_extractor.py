"""Feature extractor adapter — converts current conditions to model features."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List

from src.domain.ml.repository import FeatureExtractor
from src.domain.ml.value_objects import Feature, FeatureSet


class TemporalFeatureExtractor(FeatureExtractor):
    """Extracts temporal + lag features from current weather conditions.

    Implements the FeatureExtractor port by computing:
    - Cyclical time features (hour sin/cos, month sin/cos)
    - Day-of-week, day-of-year, weekend flag
    - Lag features from current conditions for each horizon

    This matches the feature engineering in scripts/train_model.py.
    """

    async def extract(
        self,
        current_conditions: Dict[str, float],
        city: str,
        timestamp: datetime,
        horizons: List[int],
    ) -> FeatureSet:
        """Convert current weather + timestamp into model-ready features.

        Args:
            current_conditions: Current weather values with keys:
                temperature_2m, relative_humidity_2m, surface_pressure,
                wind_speed_10m, cloud_cover, wind_direction_10m,
                dew_point_2m, precipitation.
            city: City name for categorical encoding.
            timestamp: Current timestamp for temporal features.
            horizons: Prediction horizons to generate lag features for.

        Returns:
            FeatureSet with all features ready for model input.
        """
        features = []

        # Cyclical temporal features
        hour = timestamp.hour
        month = timestamp.month
        day_of_week = timestamp.weekday()
        day_of_year = timestamp.timetuple().tm_yday
        is_weekend = 1 if day_of_week >= 5 else 0

        features.append(Feature(name="hour_sin", value=math.sin(2 * math.pi * hour / 24)))
        features.append(Feature(name="hour_cos", value=math.cos(2 * math.pi * hour / 24)))
        features.append(Feature(name="month_sin", value=math.sin(2 * math.pi * month / 12)))
        features.append(Feature(name="month_cos", value=math.cos(2 * math.pi * month / 12)))
        features.append(Feature(name="day_of_week", value=float(day_of_week)))
        features.append(Feature(name="day_of_year", value=float(day_of_year)))
        features.append(Feature(name="is_weekend", value=float(is_weekend)))

        # Lag features: current conditions used as lag for each horizon
        lag_variables = [
            "temperature_2m",
            "relative_humidity_2m",
            "surface_pressure",
            "wind_speed_10m",
            "cloud_cover",
            "wind_direction_10m",
            "dew_point_2m",
            "precipitation",
        ]

        for h in horizons:
            for var in lag_variables:
                value = current_conditions.get(var, 0.0)
                features.append(Feature(name=f"{var}_lag_{h}", value=value))

        return FeatureSet(
            features=features,
            city=city,
            generated_at=timestamp,
        )
