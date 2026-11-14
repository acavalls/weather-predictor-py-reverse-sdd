"""Weather value objects — immutable domain primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Location:
    """Geographic coordinates with optional name.

    Validates latitude (-90 to 90) and longitude (-180 to 180).
    """

    latitude: float
    longitude: float
    name: Optional[str] = None

    def __post_init__(self) -> None:
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} ({self.latitude:.4f}, {self.longitude:.4f})"
        return f"({self.latitude:.4f}, {self.longitude:.4f})"


@dataclass(frozen=True)
class Temperature:
    """Temperature in Celsius."""

    value: float

    def __post_init__(self) -> None:
        if self.value < -100:
            raise ValueError(f"Temperature too low: {self.value}°C")
        if self.value > 100:
            raise ValueError(f"Temperature too high: {self.value}°C")

    def __str__(self) -> str:
        return f"{self.value:.1f}°C"


@dataclass(frozen=True)
class Humidity:
    """Relative humidity as percentage (0-100)."""

    value: float

    def __post_init__(self) -> None:
        if not (0 <= self.value <= 100):
            raise ValueError(f"Humidity must be between 0 and 100, got {self.value}%")

    def __str__(self) -> str:
        return f"{self.value:.1f}%"


@dataclass(frozen=True)
class Pressure:
    """Atmospheric pressure in hPa (hectopascals)."""

    value: float

    def __post_init__(self) -> None:
        if not (870 <= self.value <= 1084):
            raise ValueError(f"Pressure out of range: {self.value} hPa")

    def __str__(self) -> str:
        return f"{self.value:.1f} hPa"


@dataclass(frozen=True)
class Precipitation:
    """Precipitation amount in millimeters."""

    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"Precipitation cannot be negative: {self.value} mm")

    def __str__(self) -> str:
        return f"{self.value:.1f} mm"


@dataclass(frozen=True)
class WindSpeed:
    """Wind speed in km/h."""

    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"Wind speed cannot be negative: {self.value} km/h")

    def __str__(self) -> str:
        return f"{self.value:.1f} km/h"


@dataclass(frozen=True)
class CloudCover:
    """Cloud cover as percentage (0-100)."""

    value: float

    def __post_init__(self) -> None:
        if not (0 <= self.value <= 100):
            raise ValueError(f"Cloud cover must be between 0 and 100, got {self.value}%")

    def __str__(self) -> str:
        return f"{self.value:.1f}%"
