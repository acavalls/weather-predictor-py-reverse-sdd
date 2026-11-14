"""Weather aggregate root and entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from src.domain.weather.events import DomainEvent, ForecastGenerated, ForecastRequested
from src.domain.weather.value_objects import (
    CloudCover,
    Humidity,
    Location,
    Precipitation,
    Pressure,
    Temperature,
    WindSpeed,
)


@dataclass
class Forecast:
    """Aggregate root for weather forecast at a location and time.

    Tracks the lifecycle of a forecast request: from initial request through
    data collection to final generation. Collects domain events as state changes occur.

    Attributes:
        location: Geographic location for the forecast.
        requested_at: When the forecast was requested.
        generated_at: When the forecast was fully generated (None until complete).
        temperature: Predicted temperature (None until generated).
        humidity: Predicted humidity (None until generated).
        pressure: Predicted pressure (None until generated).
        wind_speed: Predicted wind speed (None until generated).
        cloud_cover: Predicted cloud cover (None until generated).
        precipitation: Predicted precipitation (None until generated).
        _events: Collected domain events (internal).
    """

    location: Location
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generated_at: datetime | None = None
    temperature: Temperature | None = None
    humidity: Humidity | None = None
    pressure: Pressure | None = None
    wind_speed: WindSpeed | None = None
    cloud_cover: CloudCover | None = None
    precipitation: Precipitation | None = None
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Record initial forecast requested event."""
        self._record_event(
            ForecastRequested(
                location_name=self.location.name or str(self.location),
                latitude=self.location.latitude,
                longitude=self.location.longitude,
            )
        )

    @property
    def is_generated(self) -> bool:
        """Whether the forecast has been fully generated."""
        return self.generated_at is not None

    def pop_events(self) -> List[DomainEvent]:
        """Return and clear collected domain events."""
        events = list(self._events)
        self._events.clear()
        return events

    def _record_event(self, event: DomainEvent) -> None:
        """Add a domain event to the internal collection."""
        self._events.append(event)

    def generate(
        self,
        temperature: Temperature,
        humidity: Humidity,
        pressure: Pressure,
        wind_speed: WindSpeed,
        cloud_cover: CloudCover,
        precipitation: Precipitation,
    ) -> None:
        """Complete the forecast with all weather values.

        Args:
            temperature: Predicted temperature.
            humidity: Predicted relative humidity.
            pressure: Predicted atmospheric pressure.
            wind_speed: Predicted wind speed.
            cloud_cover: Predicted cloud cover.
            precipitation: Predicted precipitation amount.

        Raises:
            ValueError: If the forecast has already been generated.
        """
        if self.is_generated:
            raise ValueError("Forecast has already been generated")

        self.temperature = temperature
        self.humidity = humidity
        self.pressure = pressure
        self.wind_speed = wind_speed
        self.cloud_cover = cloud_cover
        self.precipitation = precipitation
        self.generated_at = datetime.now(timezone.utc)

        self._record_event(
            ForecastGenerated(
                location_name=self.location.name or str(self.location),
                temperature=temperature.value,
                humidity=humidity.value,
                pressure=pressure.value,
                wind_speed=wind_speed.value,
                cloud_cover=cloud_cover.value,
                precipitation=precipitation.value,
            )
        )

    def summary(self) -> str:
        """Return a human-readable summary of the forecast.

        Returns:
            String summary with all available weather values.

        Raises:
            ValueError: If the forecast has not been generated yet.
        """
        if not self.is_generated:
            raise ValueError("Forecast not yet generated")

        parts = [f"Forecast for {self.location}:"]
        if self.temperature:
            parts.append(f"  Temperature: {self.temperature}")
        if self.humidity:
            parts.append(f"  Humidity: {self.humidity}")
        if self.pressure:
            parts.append(f"  Pressure: {self.pressure}")
        if self.wind_speed:
            parts.append(f"  Wind: {self.wind_speed}")
        if self.cloud_cover:
            parts.append(f"  Cloud cover: {self.cloud_cover}")
        if self.precipitation:
            parts.append(f"  Precipitation: {self.precipitation}")
        return "\n".join(parts)
