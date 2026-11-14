"""QueryIntent value object — represents the parsed intent from a user query."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """Types of weather-related user intents."""

    FORECAST = "forecast"
    CURRENT_CONDITIONS = "current_conditions"
    HISTORICAL = "historical"
    ADVICE = "advice"
    GENERAL = "general"


_FORECAST_KEYWORDS = frozenset(
    [
        "will",
        "tomorrow",
        "next week",
        "forecast",
        "predict",
        "going to",
        "rain",
        "snow",
        "sunny",
        "cloudy",
        "temperature",
        "how cold",
        "how hot",
        "how warm",
        # Spanish
        "llover",
        "lloverá",
        "llovió",
        "mañana",
        "pasado mañana",
        "pronóstico",
        "predicción",
        "temperatura",
        "frío",
        "calor",
        "soleado",
        "nublado",
        "nieve",
        "nevando",
        "tiempo",
        "clima",
    ]
)

_ADVICE_KEYWORDS = frozenset(
    [
        "should i",
        "recommend",
        "advice",
        "bring",
        "wear",
        "umbrella",
        "jacket",
        "safe",
        "danger",
        # Spanish
        "debería",
        "recomiendas",
        "llevar",
        "paraguas",
        "chaqueta",
        "abrigo",
        "seguro",
        "peligro",
        "conviene",
    ]
)

_CURRENT_KEYWORDS = frozenset(
    [
        "now",
        "current",
        "right now",
        "at the moment",
        "today",
        # Spanish
        "ahora",
        "actual",
        "en este momento",
        "hoy",
    ]
)

_HISTORICAL_KEYWORDS = frozenset(
    [
        "last year",
        "last month",
        "yesterday",
        "historical",
        "past",
        "record",
        "average",
        # Spanish
        "año pasado",
        "mes pasado",
        "ayer",
        "histórico",
        "pasado",
        "récord",
        "promedio",
        "media",
    ]
)


@dataclass(frozen=True)
class QueryIntent:
    """Parsed intent extracted from a user's natural language query.

    Represents what the user wants to know about weather, classified
    by intent type with a confidence score.

    Attributes:
        intent_type: Classification of the query intent.
        raw_query: Original user query text.
        confidence: Confidence score of intent classification (0.0 to 1.0).
    """

    intent_type: IntentType
    raw_query: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Validate query intent fields after initialization."""
        if not self.raw_query or not self.raw_query.strip():
            raise ValueError("raw_query must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

    @property
    def is_weather_related(self) -> bool:
        """Check if the intent is weather-related."""
        return self.intent_type in (
            IntentType.FORECAST,
            IntentType.CURRENT_CONDITIONS,
            IntentType.HISTORICAL,
            IntentType.ADVICE,
        )

    @classmethod
    def from_query(cls, query: str, confidence: float = 1.0) -> QueryIntent:
        """Classify a user query into an intent type.

        Simple keyword-based classification. In production, this would
        use an NLP model or LLM-based classification.

        Args:
            query: Raw user query text.
            confidence: Confidence score for the classification.

        Returns:
            QueryIntent with classified intent type.
        """
        query_lower = query.lower()

        # Check more specific intents first; forecast is the catch-all for weather queries
        if any(kw in query_lower for kw in _CURRENT_KEYWORDS):
            intent_type = IntentType.CURRENT_CONDITIONS
        elif any(kw in query_lower for kw in _ADVICE_KEYWORDS):
            intent_type = IntentType.ADVICE
        elif any(kw in query_lower for kw in _HISTORICAL_KEYWORDS):
            intent_type = IntentType.HISTORICAL
        elif any(kw in query_lower for kw in _FORECAST_KEYWORDS):
            intent_type = IntentType.FORECAST
        else:
            intent_type = IntentType.GENERAL

        return cls(
            intent_type=intent_type,
            raw_query=query,
            confidence=confidence,
        )
