"""Weather repository ports — interfaces for external weather data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.domain.weather.value_objects import (
    CloudCover,
    Humidity,
    Location,
    Precipitation,
    Pressure,
    Temperature,
    WindSpeed,
)


class CurrentWeather:
    """Current weather conditions at a specific location.

    Attributes:
        location: Geographic location.
        temperature: Current temperature.
        humidity: Current relative humidity.
        pressure: Current atmospheric pressure.
        wind_speed: Current wind speed.
        cloud_cover: Current cloud cover percentage.
        precipitation: Current precipitation amount.
    """

    def __init__(
        self,
        location: Location,
        temperature: Temperature,
        humidity: Humidity,
        pressure: Pressure,
        wind_speed: WindSpeed,
        cloud_cover: CloudCover,
        precipitation: Precipitation,
    ) -> None:
        self.location = location
        self.temperature = temperature
        self.humidity = humidity
        self.pressure = pressure
        self.wind_speed = wind_speed
        self.cloud_cover = cloud_cover
        self.precipitation = precipitation

    def to_features(self) -> Dict[str, float]:
        """Convert current weather to feature dict for ML model.

        Returns:
            Dictionary of feature names to numeric values.
        """
        return {
            "temperature": self.temperature.value,
            "humidity": self.humidity.value,
            "pressure": self.pressure.value,
            "wind_speed": self.wind_speed.value,
            "cloud_cover": self.cloud_cover.value,
            "precipitation": self.precipitation.value,
        }


class WeatherProvider(ABC):
    """Port for fetching weather data from external providers.

    Implementations: OpenMeteoAdapter, MeteostatAdapter, MockWeatherProvider.
    """

    @abstractmethod
    async def geocode(self, city_name: str) -> Location:
        """Resolve a city name to geographic coordinates.

        Args:
            city_name: Human-readable city name.

        Returns:
            Location with resolved coordinates and name.

        Raises:
            NotFoundError: If the city cannot be found.
        """
        pass

    @abstractmethod
    async def get_current_weather(self, location: Location) -> CurrentWeather:
        """Fetch current weather conditions for a location.

        Args:
            location: Geographic location.

        Returns:
            CurrentWeather with all measured variables.

        Raises:
            NotFoundError: If weather data is unavailable.
        """
        pass

    @abstractmethod
    async def get_historical_weather(self, location: Location, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch historical weather data for a location and date range.

        Args:
            location: Geographic location.
            start_date: Start date in ISO format (YYYY-MM-DD).
            end_date: End date in ISO format (YYYY-MM-DD).

        Returns:
            List of hourly weather records.

        Raises:
            NotFoundError: If historical data is unavailable.
        """
        pass
