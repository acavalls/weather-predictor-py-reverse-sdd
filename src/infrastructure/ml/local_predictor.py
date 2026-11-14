"""Local ML predictor adapter — loads .pkl model and generates predictions."""

from __future__ import annotations

import hashlib
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd

from src.domain.ml.repository import ModelPredictor
from src.domain.ml.value_objects import FeatureSet, ModelMetadata, ModelVersion, PredictionResult
from src.domain.shared.errors import NotFoundError
from src.infrastructure.ml.model_wrapper import MultiOutputRegressorWithProgress

# Register MultiOutputRegressorWithProgress under __main__ so pickle
# can resolve it when loading model.pkl (trained via scripts/train_model.py
# which pickled the class as __main__.MultiOutputRegressorWithProgress).
_original_main = sys.modules.get("__main__")
_fake_main = types.ModuleType("__main__")
_fake_main.MultiOutputRegressorWithProgress = MultiOutputRegressorWithProgress  # type: ignore[attr-defined]
if _original_main is not None:
    for attr in dir(_original_main):
        if not attr.startswith("__"):
            setattr(_fake_main, attr, getattr(_original_main, attr))
sys.modules["__main__"] = _fake_main


class LocalPredictor(ModelPredictor):
    """Adapter that loads a scikit-learn .pkl model and runs predictions.

    Wraps the model artifact from scripts/train_model.py and implements
    the ModelPredictor port.

    Args:
        default_model_path: Default path to model.pkl. Can be overridden per call.
    """

    def __init__(self, default_model_path: str = "models/model.pkl") -> None:
        self._default_model_path = default_model_path
        self._pipeline: Any = None
        self._model_artifact: Dict[str, Any] = {}

    async def load_model(self, model_path: str | None = None) -> ModelMetadata:
        """Load trained model from .pkl file.

        Args:
            model_path: Path to model artifact. Uses default if None.

        Returns:
            ModelMetadata with version, columns, horizons, and scores.

        Raises:
            FileNotFoundError: If model file does not exist.
            ValueError: If model artifact is corrupted or missing keys.
        """
        path = Path(model_path or self._default_model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        artifact = joblib.load(path)
        self._model_artifact = artifact
        self._pipeline = artifact["pipeline"]

        horizons = artifact["horizons"]
        trained_at = self._extract_trained_at(path)

        version = ModelVersion(
            version=self._compute_version_hash(path),
            trained_at=trained_at,
            horizons=tuple(horizons),
        )

        return ModelMetadata(
            version=version,
            feature_columns=artifact["feature_columns"],
            target_columns=artifact["target_columns"],
            horizons=horizons,
            train_score=artifact.get("train_score", 0.0),
            test_score=artifact.get("test_score", 0.0),
        )

    async def predict(
        self,
        model: ModelMetadata,
        feature_set: FeatureSet,
        horizons: List[int],
    ) -> PredictionResult:
        """Generate predictions using loaded model.

        Args:
            model: Loaded model metadata.
            feature_set: Input features.
            horizons: Horizons to predict.

        Returns:
            PredictionResult with all target values per horizon.

        Raises:
            ValueError: If model not loaded or features mismatch.
        """
        if self._pipeline is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        # Build input dict matching model schema
        features = feature_set.to_dict()
        input_dict = self._align_features(features, model.feature_columns, feature_set.city)

        # Run prediction (use DataFrame so ColumnTransformer can resolve named columns)
        X = pd.DataFrame(
            [{col: input_dict.get(col, 0.0) for col in model.feature_columns}],
            columns=model.feature_columns,
        )
        raw_predictions = self._pipeline.predict(X)

        # Parse results into horizon-structured dict
        predictions = self._parse_predictions(raw_predictions, model.target_columns, horizons)

        return PredictionResult(
            model_version=model.version,
            predictions=predictions,
            predicted_at=datetime.now(timezone.utc),
        )

    async def get_model_version(self, model_path: str | None = None) -> ModelVersion:
        """Read model metadata without loading full pipeline.

        Args:
            model_path: Path to model artifact. Uses default if None.

        Returns:
            ModelVersion with metadata.
        """
        path = Path(model_path or self._default_model_path)
        if not path.exists():
            raise NotFoundError(f"Model file not found: {path}")

        artifact = joblib.load(path)
        horizons = artifact["horizons"]
        trained_at = self._extract_trained_at(path)

        return ModelVersion(
            version=self._compute_version_hash(path),
            trained_at=trained_at,
            horizons=tuple(horizons),
        )

    @staticmethod
    def _compute_version_hash(path: Path) -> str:
        """Compute a short hash of the model file as version identifier."""
        content = path.read_bytes()
        return hashlib.md5(content).hexdigest()[:8]

    @staticmethod
    def _extract_trained_at(path: Path) -> datetime:
        """Use file modification time as training timestamp."""
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc)

    @staticmethod
    def _align_features(
        features: Dict[str, Any],
        expected_columns: List[str],
        city: str,
    ) -> Dict[str, Any]:
        """Align feature dict to model's expected column order.

        Fills missing columns with 0.0 and ignores extra columns.
        The city column receives the actual city name so that the
        OneHotEncoder in the pipeline's ColumnTransformer can encode it
        (unknown cities produce all-zeros via handle_unknown="ignore").

        Args:
            features: Feature dict from FeatureSet.
            expected_columns: Model's expected feature column names.
            city: City name for categorical encoding.

        Returns:
            Aligned dict with only expected columns.
        """
        aligned: Dict[str, Any] = {}
        for col in expected_columns:
            if col == "city":
                aligned[col] = city
            else:
                aligned[col] = float(features.get(col, 0.0))
        return aligned

    @staticmethod
    def _parse_predictions(
        raw: np.ndarray,
        target_columns: List[str],
        horizons: List[int],
    ) -> Dict[int, Dict[str, float]]:
        """Parse flat prediction array into nested {horizon: {target: value}} dict.

        Target columns follow naming: {variable}_target_{horizon}

        Args:
            raw: 1D or 2D array of predictions.
            target_columns: List of target column names from model.
            horizons: Horizons to extract.

        Returns:
            Nested dict of predictions per horizon.
        """
        values = raw[0] if raw.ndim == 2 else raw
        predictions: Dict[int, Dict[str, float]] = {}

        for col_name, value in zip(target_columns, values):
            # Parse column name: e.g., "temperature_2m_target_24"
            parts = col_name.rsplit("_target_", 1)
            if len(parts) != 2:
                continue
            variable_name, horizon_str = parts
            horizon = int(horizon_str)

            if horizon not in horizons:
                continue

            if horizon not in predictions:
                predictions[horizon] = {}

            predictions[horizon][variable_name] = float(value)

        return predictions
