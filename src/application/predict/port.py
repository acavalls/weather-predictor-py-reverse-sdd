"""Predict use case port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from src.application.predict.command import PredictCommand


@dataclass(frozen=True)
class PredictResult:
    """Result of a prediction use case execution.

    Attributes:
        city: City name the prediction was for.
        location_name: Resolved location name from geocoding.
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        predictions: Nested dict {horizon: {target_name: value}}.
        model_version: Model version hash.
        predicted_at: When the prediction was generated.
    """

    city: str
    location_name: str
    latitude: float
    longitude: float
    predictions: Dict[int, Dict[str, float]]
    model_version: str
    predicted_at: datetime


class IPredictUseCase(ABC):
    """Driver port for the prediction use case.

    Implementations: PredictHandler.
    """

    @abstractmethod
    async def execute(self, command: PredictCommand) -> PredictResult:
        """Execute a weather prediction.

        Args:
            command: Prediction command with city and horizons.

        Returns:
            PredictResult with all predicted values per horizon.

        Raises:
            NotFoundError: If the city or weather data is not found.
            ValueError: If the prediction fails.
        """
        pass
