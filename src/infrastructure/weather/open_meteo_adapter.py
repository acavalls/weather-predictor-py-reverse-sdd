"""Open-Meteo API adapter — implements WeatherProvider port.

Connects to Open-Meteo's free APIs:
- Geocoding: city name → coordinates
- Forecast: current weather conditions
- Historical: archived weather data for model training
"""

from __future__ import annotations

from typing import Any, Dict, List

import httpx

from src.domain.shared.errors import NotFoundError
from src.domain.weather.repository import CurrentWeather, WeatherProvider
from src.domain.weather.value_objects import (
    CloudCover,
    Humidity,
    Location,
    Precipitation,
    Pressure,
    Temperature,
    WindSpeed,
)


class OpenMeteoAdapter(WeatherProvider):
    """Adapter for Open-Meteo APIs.

    Implements WeatherProvider using Open-Meteo's free endpoints:
    - /v1/search for geocoding (geocoding-api.open-meteo.com)
    - /v1/forecast for current conditions
    - /v1/archive for historical data

    Args:
        base_url: Open-Meteo API base URL (default: https://api.open-meteo.com).
        geocoding_url: Geocoding API URL (default: https://geocoding-api.open-meteo.com).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "https://api.open-meteo.com",
        geocoding_url: str = "https://geocoding-api.open-meteo.com",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._geocoding_url = geocoding_url.rstrip("/")
        self._timeout = timeout

    async def geocode(self, city_name: str) -> Location:
        """Resolve city name to coordinates via Open-Meteo Geocoding API.

        Args:
            city_name: Human-readable city name.

        Returns:
            Location with resolved coordinates.

        Raises:
            NotFoundError: If no matching location is found.
        """
        url = f"{self._geocoding_url}/v1/search"
        params: Dict[str, Any] = {"name": city_name, "count": 1, "language": "en", "format": "json"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        if not results:
            raise NotFoundError(f"Location not found: {city_name}")

        first = results[0]
        return Location(
            latitude=float(first["latitude"]),
            longitude=float(first["longitude"]),
            name=first.get("name", city_name),
        )

    async def get_current_weather(self, location: Location) -> CurrentWeather:
        """Fetch current weather conditions via Open-Meteo Forecast API.

        Requests: temperature_2m, relative_humidity_2m, surface_pressure,
        wind_speed_10m, cloud_cover, precipitation.

        Args:
            location: Geographic location.

        Returns:
            CurrentWeather with all measured variables.

        Raises:
            NotFoundError: If weather data is unavailable.
        """
        url = f"{self._base_url}/v1/forecast"
        params: Dict[str, Any] = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,cloud_cover,precipitation",
            "timezone": "auto",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        current = data.get("current", {})
        if not current:
            raise NotFoundError(f"No current weather data for {location}")

        return CurrentWeather(
            location=location,
            temperature=Temperature(value=float(current.get("temperature_2m", 0))),
            humidity=Humidity(value=float(current.get("relative_humidity_2m", 0))),
            pressure=Pressure(value=float(current.get("surface_pressure", 1013))),
            wind_speed=WindSpeed(value=float(current.get("wind_speed_10m", 0))),
            cloud_cover=CloudCover(value=float(current.get("cloud_cover", 0))),
            precipitation=Precipitation(value=float(current.get("precipitation", 0))),
        )

    async def get_historical_weather(self, location: Location, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch historical weather data via Open-Meteo Archive API.

        Args:
            location: Geographic location.
            start_date: Start date in ISO format (YYYY-MM-DD).
            end_date: End date in ISO format (YYYY-MM-DD).

        Returns:
            List of hourly weather records as dictionaries.

        Raises:
            NotFoundError: If historical data is unavailable.
        """
        url = f"{self._base_url}/v1/archive"
        params: Dict[str, Any] = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": (
                "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,"
                "cloud_cover,precipitation,wind_direction_10m,dew_point_2m"
            ),
            "timezone": "auto",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        hourly = data.get("hourly", {})
        if not hourly:
            raise NotFoundError(f"No historical data for {location} ({start_date} to {end_date})")

        # Convert hourly dict to list of records
        times = hourly.get("time", [])
        records: List[Dict[str, Any]] = []
        for i, timestamp in enumerate(times):
            record: Dict[str, Any] = {"timestamp": timestamp}
            for key in hourly:
                if key != "time" and i < len(hourly[key]):
                    record[key] = hourly[key][i]
            records.append(record)

        return records
