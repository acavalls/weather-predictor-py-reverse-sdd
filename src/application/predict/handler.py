"""Predict use case handler — orchestrates weather + ML prediction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.application.predict.command import PredictCommand
from src.application.predict.port import IPredictUseCase, PredictResult
from src.domain.ml.repository import FeatureExtractor, ModelPredictor
from src.domain.ml.value_objects import ModelMetadata
from src.domain.weather.repository import WeatherProvider


class PredictHandler(IPredictUseCase):
    """Handler that orchestrates the prediction flow.

    Injects driven ports (WeatherProvider, ModelPredictor, FeatureExtractor)
    and implements the driver port (IPredictUseCase).

    Flow:
        1. Geocode city name → coordinates
        2. Fetch current weather at location
        3. Extract features from current conditions
        4. Run ML prediction
        5. Return structured result
    """

    def __init__(
        self,
        weather_provider: WeatherProvider,
        model_predictor: ModelPredictor,
        feature_extractor: FeatureExtractor,
        model_path: str = "model.pkl",
        default_horizons: Optional[List[int]] = None,
    ) -> None:
        self._weather_provider = weather_provider
        self._model_predictor = model_predictor
        self._feature_extractor = feature_extractor
        self._model_path = model_path
        self._default_horizons = default_horizons or [6, 12, 24]
        self._model: Optional[ModelMetadata] = None

    async def _ensure_model_loaded(self) -> ModelMetadata:
        """Load model on first use (lazy initialization)."""
        if self._model is None:
            self._model = await self._model_predictor.load_model(self._model_path)
        return self._model

    async def execute(self, command: PredictCommand) -> PredictResult:
        """Execute prediction for a city.

        Args:
            command: Prediction command with city and horizons.

        Returns:
            PredictResult with predictions per horizon.
        """
        horizons = command.horizons if command.horizons else self._default_horizons

        # 1. Geocode
        location = await self._weather_provider.geocode(command.city)

        # 2. Fetch current weather
        current_weather = await self._weather_provider.get_current_weather(location)

        # 3. Load model
        model = await self._ensure_model_loaded()

        # 4. Extract features
        current_conditions = self._weather_to_conditions(current_weather)
        feature_set = await self._feature_extractor.extract(
            current_conditions=current_conditions,
            city=location.name or command.city,
            timestamp=datetime.now(timezone.utc),
            horizons=horizons,
        )

        # 5. Predict
        prediction_result = await self._model_predictor.predict(
            model=model,
            feature_set=feature_set,
            horizons=horizons,
        )

        return PredictResult(
            city=command.city,
            location_name=location.name or str(location),
            latitude=location.latitude,
            longitude=location.longitude,
            predictions=prediction_result.predictions,
            model_version=prediction_result.model_version.version,
            predicted_at=prediction_result.predicted_at,
        )

    @staticmethod
    def _weather_to_conditions(current_weather) -> Dict[str, float]:
        """Convert CurrentWeather domain object to feature dict.

        Matches the keys expected by FeatureExtractor (Open-Meteo variable names).

        Args:
            current_weather: CurrentWeather from WeatherProvider.

        Returns:
            Dict with Open-Meteo variable names as keys.
        """
        return {
            "temperature_2m": current_weather.temperature.value,
            "relative_humidity_2m": current_weather.humidity.value,
            "surface_pressure": current_weather.pressure.value,
            "wind_speed_10m": current_weather.wind_speed.value,
            "cloud_cover": current_weather.cloud_cover.value,
            "precipitation": current_weather.precipitation.value,
        }
