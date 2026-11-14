"""Weather domain services — stateless logic that doesn't fit an entity."""

from __future__ import annotations

from src.domain.weather.value_objects import CloudCover, Humidity, Pressure


class WeatherInterpretationService:
    """Interprets weather conditions using meteorological principles.

    Stateless service that analyzes weather value objects and returns
    qualitative assessments. Used by RAG to provide context for the LLM.
    """

    @staticmethod
    def is_rain_likely(humidity: Humidity, pressure: Pressure) -> bool:
        """Assess rain probability using Magnus Law heuristic.

        High humidity (>80%) combined with low pressure (<1010 hPa)
        indicates high rain probability.

        Args:
            humidity: Current relative humidity.
            pressure: Current atmospheric pressure.

        Returns:
            True if conditions suggest rain is likely.
        """
        return humidity.value > 80 and pressure.value < 1010

    @staticmethod
    def pressure_trend_description(pressure: Pressure) -> str:
        """Describe the pressure level qualitatively.

        Args:
            pressure: Atmospheric pressure value.

        Returns:
            Human-readable pressure description.
        """
        if pressure.value < 1000:
            return "very low — storm conditions possible"
        if pressure.value < 1010:
            return "low — unsettled weather likely"
        if pressure.value < 1020:
            return "normal — typical conditions"
        if pressure.value < 1030:
            return "high — stable weather expected"
        return "very high — clear skies likely"

    @staticmethod
    def humidity_description(humidity: Humidity) -> str:
        """Describe humidity level qualitatively.

        Args:
            humidity: Relative humidity value.

        Returns:
            Human-readable humidity description.
        """
        if humidity.value < 30:
            return "very dry"
        if humidity.value < 50:
            return "comfortable"
        if humidity.value < 70:
            return "moderate"
        if humidity.value < 85:
            return "high — muggy conditions"
        return "very high — precipitation likely"

    @staticmethod
    def cloud_cover_description(cloud_cover: CloudCover) -> str:
        """Describe cloud cover qualitatively.

        Args:
            cloud_cover: Cloud cover percentage.

        Returns:
            Human-readable cloud description.
        """
        if cloud_cover.value < 10:
            return "clear skies"
        if cloud_cover.value < 30:
            return "mostly clear"
        if cloud_cover.value < 70:
            return "partly cloudy"
        if cloud_cover.value < 90:
            return "mostly cloudy"
        return "overcast"
