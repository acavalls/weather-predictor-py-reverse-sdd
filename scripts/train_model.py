"""Train multi-output regression model on historical weather data.

Reads CSV from download_historical.py, engineers features (hour, month, day,
current conditions), trains Gradient Boosting regressors for each target
variable (temperature, humidity, pressure, wind, cloud_cover, precipitation),
and saves the trained pipeline as model.pkl.

Usage:
    python scripts/train_model.py
    python scripts/train_model.py --input data/historical_weather.csv
    python scripts/train_model.py --output models/model.pkl
    python scripts/train_model.py --horizon 6 12 24 48 72 168
"""

import argparse
import logging
from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from tqdm import tqdm

# Import from shared module so pickle references are resolvable at prediction time.
from src.infrastructure.ml.model_wrapper import MultiOutputRegressorWithProgress

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TARGET_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "cloud_cover",
    "precipitation",
]

NUMERIC_FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "surface_pressure",
    "wind_speed_10m",
    "cloud_cover",
    "wind_direction_10m",
    "dew_point_2m",
    "precipitation",
]

CATEGORICAL_FEATURES = ["city"]


def load_data(input_path: str) -> pd.DataFrame:
    """Load and validate historical weather CSV."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}. Run download_historical.py first.")

    df = pd.read_csv(path, parse_dates=["datetime"])
    logger.info(f"Loaded {len(df)} rows from {input_path}")

    missing = set(TARGET_VARIABLES) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")

    df = df.dropna(subset=TARGET_VARIABLES)
    logger.info(f"After dropping NaN targets: {len(df)} rows")
    return df


def engineer_features(df: pd.DataFrame, horizons: List[int]) -> pd.DataFrame:
    """Create temporal features and lagged target features for each horizon."""
    df = df.copy()

    # Temporal features
    df["hour"] = df["datetime"].dt.hour
    df["month"] = df["datetime"].dt.month
    df["day_of_week"] = df["datetime"].dt.dayofweek
    df["day_of_year"] = df["datetime"].dt.dayofyear
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # Cyclical encoding for hour and month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # Lagged features per horizon
    for h in horizons:
        for var in TARGET_VARIABLES:
            df[f"{var}_lag_{h}"] = df.groupby("city")[var].shift(h)

    df = df.dropna()
    logger.info(f"After feature engineering + lag dropna: {len(df)} rows")
    return df


def build_feature_columns(horizons: List[int]) -> List[str]:
    """Return list of feature column names for model training."""
    cols = [
        "hour_sin",
        "hour_cos",
        "month_sin",
        "month_cos",
        "day_of_week",
        "day_of_year",
        "is_weekend",
    ]
    for h in horizons:
        for var in TARGET_VARIABLES:
            cols.append(f"{var}_lag_{h}")
    cols.append("city")
    return cols


def build_target_columns(horizons: List[int]) -> List[str]:
    """Return list of target column names (one per variable per horizon)."""
    cols = []
    for h in horizons:
        for var in TARGET_VARIABLES:
            cols.append(f"{var}_target_{h}")
    return cols


def prepare_targets(df: pd.DataFrame, horizons: List[int]) -> pd.DataFrame:
    """Create target columns: value of each variable at horizon h."""
    df = df.copy()
    for h in horizons:
        for var in TARGET_VARIABLES:
            df[f"{var}_target_{h}"] = df.groupby("city")[var].shift(-h)
    df = df.dropna()
    return df


def train_model(
    input_path: str = "data/historical_weather.csv",
    output_path: str = "models/model.pkl",
    horizons: Optional[List[int]] = None,
    test_size: float = 0.2,
    n_estimators: int = 200,
    max_depth: int = 5,
    learning_rate: float = 0.1,
) -> dict:
    """Full training pipeline: load → engineer → split → train → save."""
    if horizons is None:
        horizons = [6, 12, 24, 48, 72, 168]

    # Load and engineer
    df = load_data(input_path)
    df = prepare_targets(df, horizons)
    df = engineer_features(df, horizons)

    feature_cols = build_feature_columns(horizons)
    target_cols = build_target_columns(horizons)

    X = df[feature_cols]
    y = df[target_cols]

    # Train/test split (time-aware: last portion as test)
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    logger.info(f"Train set: {len(X_train)} rows, Test set: {len(X_test)} rows")
    logger.info(f"Features: {len(feature_cols)}, Targets: {len(target_cols)}")

    # Preprocessor
    numeric_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder(handle_unknown="ignore", sparse_output=False)

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, [c for c in feature_cols if c != "city"]),
            ("cat", categorical_transformer, ["city"]),
        ]
    )

    # Multi-output Gradient Boosting with progress bar
    base_estimator = GradientBoostingRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        random_state=42,
        subsample=0.8,
    )

    logger.info(f"Training {len(target_cols)} target models...")
    preprocessor.fit(X_train)
    X_train_transformed = preprocessor.transform(X_train)
    X_test_transformed = preprocessor.transform(X_test)

    trained_estimators = []
    for i, target_col in enumerate(tqdm(target_cols, desc="Training targets")):
        logger.info(f"[{i + 1}/{len(target_cols)}] Training: {target_col}")
        estimator = clone(base_estimator)
        estimator.fit(X_train_transformed, y_train.iloc[:, i])
        trained_estimators.append(estimator)

    model = MultiOutputRegressorWithProgress(trained_estimators)

    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("regressor", model),
        ]
    )

    logger.info("Evaluating model...")
    train_score = model.score(X_train_transformed, y_train)
    test_score = model.score(X_test_transformed, y_test)
    logger.info(f"Train R²: {train_score:.4f}")
    logger.info(f"Test R²:  {test_score:.4f}")

    # Per-target metrics
    y_pred = model.predict(X_test_transformed)
    for i, col in enumerate(target_cols):
        ss_res = np.sum((y_test.iloc[:, i].values - y_pred[:, i]) ** 2)
        ss_tot = np.sum((y_test.iloc[:, i].values - y_test.iloc[:, i].mean()) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        mae = np.mean(np.abs(y_test.iloc[:, i].values - y_pred[:, i]))
        logger.info(f"  {col}: R²={r2:.4f}, MAE={mae:.4f}")

    # Save
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    model_artifact = {
        "pipeline": pipeline,
        "feature_columns": feature_cols,
        "target_columns": target_cols,
        "horizons": horizons,
        "train_score": train_score,
        "test_score": test_score,
        "n_train_samples": len(X_train),
        "n_test_samples": len(X_test),
    }

    joblib.dump(model_artifact, output)
    logger.info(f"Model saved to {output}")

    return model_artifact


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Train weather prediction model")
    parser.add_argument(
        "--input",
        default="data/historical_weather.csv",
        help="Input CSV path (default: data/historical_weather.csv)",
    )
    parser.add_argument(
        "--output",
        default="models/model.pkl",
        help="Output model path (default: models/model.pkl)",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        nargs="+",
        default=[6, 12, 24, 48, 72, 168],
        help="Prediction horizons in hours (default: 6 12 24 48 72 168)",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split ratio (default: 0.2)",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=200,
        help="Number of boosting estimators (default: 200)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Max tree depth (default: 5)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.1,
        help="Learning rate (default: 0.1)",
    )
    args = parser.parse_args()

    train_model(
        input_path=args.input,
        output_path=args.output,
        horizons=args.horizon,
        test_size=args.test_size,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
    )


if __name__ == "__main__":
    main()
