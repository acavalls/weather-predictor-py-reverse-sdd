"""ML value objects — immutable domain primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass(frozen=True)
class Feature:
    """Single model feature with name and numeric value.

    Attributes:
        name: Feature identifier matching model training schema.
        value: Numeric feature value.
    """

    name: str
    value: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Feature name cannot be empty")


@dataclass(frozen=True)
class FeatureSet:
    """Collection of features ready for model input.

    Immutable bundle of all features computed from current conditions
    and temporal context.

    Attributes:
        features: Ordered list of Feature objects.
        city: City name used for categorical encoding.
        generated_at: Timestamp when features were computed.
    """

    features: List[Feature]
    city: str
    generated_at: datetime

    def to_dict(self) -> Dict[str, float]:
        """Convert feature set to dict matching model input schema.

        Returns:
            Dictionary mapping feature names to numeric values.
        """
        return {f.name: f.value for f in self.features}

    @property
    def feature_names(self) -> List[str]:
        return [f.name for f in self.features]


@dataclass(frozen=True)
class ModelVersion:
    """Semantic version string for a trained model.

    Attributes:
        version: Version string (e.g., "1.0.0", "2024.01.15").
        trained_at: Timestamp when model was trained.
        horizons: Prediction horizons in hours this model supports.
    """

    version: str
    trained_at: datetime
    horizons: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("Model version cannot be empty")
        if not self.horizons:
            raise ValueError("Model must have at least one horizon")


@dataclass(frozen=True)
class ModelMetadata:
    """Read-only metadata about a trained model.

    No mutable state. Loaded once from the .pkl artifact and used
    to validate predictions against the model's capabilities.

    Attributes:
        version: Model version identifier.
        feature_columns: Expected feature column names.
        target_columns: Target column names the model predicts.
        horizons: Supported prediction horizons in hours.
        train_score: R² score on training data.
        test_score: R² score on test data.
    """

    version: ModelVersion
    feature_columns: List[str]
    target_columns: List[str]
    horizons: List[int]
    train_score: float = 0.0
    test_score: float = 0.0

    def supports_horizon(self, horizon: int) -> bool:
        return horizon in self.horizons

    def has_features(self, feature_names: List[str]) -> bool:
        """Check if all required features (except city) are present."""
        required = set(self.feature_columns) - {"city"}
        return required.issubset(set(feature_names))


@dataclass(frozen=True)
class PredictionResult:
    """Output of a model prediction with all target values per horizon.

    Attributes:
        model_version: Version of the model that generated this prediction.
        predictions: Nested dict {horizon: {target_name: value}}.
        predicted_at: Timestamp when prediction was generated.
    """

    model_version: ModelVersion
    predictions: Dict[int, Dict[str, float]]
    predicted_at: datetime

    def __post_init__(self) -> None:
        if not self.predictions:
            raise ValueError("Prediction result must contain at least one prediction")

    def get_temperature(self, horizon: int) -> float:
        """Get predicted temperature for a given horizon in hours."""
        return self.predictions[horizon]["temperature_2m"]

    def get_humidity(self, horizon: int) -> float:
        """Get predicted relative humidity for a given horizon in hours."""
        return self.predictions[horizon]["relative_humidity_2m"]

    def get_pressure(self, horizon: int) -> float:
        """Get predicted surface pressure for a given horizon in hours."""
        return self.predictions[horizon]["surface_pressure"]

    def get_wind_speed(self, horizon: int) -> float:
        """Get predicted wind speed for a given horizon in hours."""
        return self.predictions[horizon]["wind_speed_10m"]

    def get_cloud_cover(self, horizon: int) -> float:
        """Get predicted cloud cover for a given horizon in hours."""
        return self.predictions[horizon]["cloud_cover"]

    def get_precipitation(self, horizon: int) -> float:
        """Get predicted precipitation for a given horizon in hours."""
        return self.predictions[horizon]["precipitation"]
