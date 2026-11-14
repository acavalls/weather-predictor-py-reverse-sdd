"""Agent domain events — facts about what happened in the agent context."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.weather.events import DomainEvent


@dataclass(frozen=True)
class QueryReceived(DomainEvent):
    """A user query was received by the agent.

    Attributes:
        session_id: Unique identifier for the chat session.
        query_text: The raw user query text.
        intent_type: Classified intent type (forecast, advice, etc.).
        location_name: Extracted location name (if any).
    """

    session_id: str = ""
    query_text: str = ""
    intent_type: str = ""
    location_name: str = ""


@dataclass(frozen=True)
class ResponseGenerated(DomainEvent):
    """A response was generated for a user query.

    Attributes:
        session_id: Unique identifier for the chat session.
        response_text: The generated natural language response.
        used_rag: Whether RAG retrieval was used in generating the response.
        used_ml_prediction: Whether ML prediction numbers were included.
        retrieved_doc_count: Number of RAG documents retrieved.
    """

    session_id: str = ""
    response_text: str = ""
    used_rag: bool = False
    used_ml_prediction: bool = False
    retrieved_doc_count: int = 0
