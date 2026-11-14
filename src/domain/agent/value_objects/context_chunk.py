"""ContextChunk value object for the agent domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextChunk:
    """A piece of context attached to a chat session turn.

    Represents a specific type of information used during response generation,
    such as weather data, ML predictions, or RAG-retrieved documents.

    Attributes:
        chunk_type: Type of context (weather, ml_prediction, rag_doc, etc.).
        content: The actual context data as a string.
        source: Origin of the context (e.g., "open_meteo", "model_v1", "pgvector").
        metadata: Additional metadata about this context chunk.
    """

    chunk_type: str
    content: str
    source: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate context chunk fields after initialization."""
        if not self.chunk_type or not self.chunk_type.strip():
            raise ValueError("chunk_type must not be empty")
        if not self.content or not self.content.strip():
            raise ValueError("content must not be empty")
        if not self.source or not self.source.strip():
            raise ValueError("source must not be empty")
