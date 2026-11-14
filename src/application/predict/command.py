"""Predict command DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class PredictCommand:
    """Command to request a weather prediction.

    Attributes:
        city: City name for the prediction.
        horizons: Prediction horizons in hours. Defaults to [6, 12, 24].
    """

    city: str
    horizons: List[int] = field(default_factory=lambda: [6, 12, 24])

    def __post_init__(self) -> None:
        if not self.city:
            raise ValueError("City name cannot be empty")
        if not self.horizons:
            raise ValueError("At least one horizon is required")
