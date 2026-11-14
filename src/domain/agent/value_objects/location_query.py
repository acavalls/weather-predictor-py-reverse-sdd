"""LocationQuery value object — represents a location extracted from a query."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.weather.value_objects import Location


@dataclass(frozen=True)
class LocationQuery:
    """Location information extracted from a user query.

    Wraps a Location value object with additional query-specific metadata
    about how the location was identified (explicit mention, inference, etc.).

    Attributes:
        location: The resolved geographic location.
        is_explicit: Whether the location was explicitly mentioned in the query.
        raw_mention: The original text mention (e.g., "Madrid", "the capital of Spain").
    """

    location: Location
    is_explicit: bool = True
    raw_mention: str = ""

    def __post_init__(self) -> None:
        """Validate location query fields after initialization."""
        if not self.raw_mention or not self.raw_mention.strip():
            raise ValueError("raw_mention must not be empty")
