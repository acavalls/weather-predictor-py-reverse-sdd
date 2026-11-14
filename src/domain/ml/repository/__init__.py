"""ML repository ports (interfaces)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List

from src.domain.ml.value_objects import FeatureSet, ModelMetadata, ModelVersion, PredictionResult


class ModelPredictor(ABC):
    """Port for generating predictions using a trained ML model.

    Implementations: LocalPredictor (loads .pkl), RemotePredictor (API call).
    """

    @abstractmethod
    async def load_model(self, model_path: str) -> ModelMetadata:
        """Load a trained model from storage.

        Args:
            model_path: Path to the model artifact (.pkl file).

        Returns:
            ModelMetadata with version, columns, horizons, and scores.

        Raises:
            FileNotFoundError: If the model file does not exist.
            ValueError: If the model artifact is corrupted.
        """
        pass

    @abstractmethod
    async def predict(self, model: ModelMetadata, feature_set: FeatureSet, horizons: List[int]) -> PredictionResult:
        """Generate predictions for given features and horizons.

        Args:
            model: Loaded model metadata.
            feature_set: Input features for prediction.
            horizons: Which horizons to predict (subset of model's horizons).

        Returns:
            PredictionResult with all target values per horizon.

        Raises:
            ValueError: If features don't match model schema.
        """
        pass

    @abstractmethod
    async def get_model_version(self, model_path: str) -> ModelVersion:
        """Read model metadata without loading the full model.

        Args:
            model_path: Path to the model artifact.

        Returns:
            ModelVersion with version, trained_at, and horizons.
        """
        pass


class FeatureExtractor(ABC):
    """Port for converting current weather conditions into model features.

    Implementations: TemporalFeatureExtractor, CachedFeatureExtractor.
    """

    @abstractmethod
    async def extract(
        self,
        current_conditions: Dict[str, float],
        city: str,
        timestamp: datetime,
        horizons: List[int],
    ) -> FeatureSet:
        """Convert current weather + temporal context into feature vector.

        Args:
            current_conditions: Dict of current weather values
                (temperature, humidity, pressure, wind_speed, cloud_cover, precipitation).
            city: City name for categorical encoding.
            timestamp: Current timestamp for temporal feature computation.
            horizons: Prediction horizons to prepare lag features for.

        Returns:
            FeatureSet with all features ready for model input.
        """
        pass
