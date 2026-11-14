"""Weather domain events — facts about what happened in the weather context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""

    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ForecastRequested(DomainEvent):
    """A forecast was requested for a location.

    Attributes:
        location_name: Human-readable location name.
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
    """

    location_name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass(frozen=True)
class ForecastGenerated(DomainEvent):
    """A forecast was successfully generated with weather data.

    Attributes:
        location_name: Human-readable location name.
        temperature: Predicted temperature in Celsius.
        humidity: Predicted relative humidity percentage.
        pressure: Predicted atmospheric pressure in hPa.
    """

    location_name: str = ""
    temperature: float = 0.0
    humidity: float = 0.0
    pressure: float = 0.0
    wind_speed: float = 0.0
    cloud_cover: float = 0.0
    precipitation: float = 0.0
