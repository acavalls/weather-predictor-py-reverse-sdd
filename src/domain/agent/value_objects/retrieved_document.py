"""RetrievedDocument value object for RAG knowledge base."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class RetrievedDocument:
    """Document retrieved from the vector knowledge base via semantic search.

    Represents a single meteorological principle, law, formula, or interpretation
    rule that was found relevant to a weather prediction query.

    Attributes:
        id: Unique identifier for the document.
        title: Short descriptive title (e.g., "Magnus Law", "Clausius-Clapeyron").
        content: Full text of the meteorological principle or rule.
        category: Classification of the document type (law, formula, rule, pattern).
        similarity_score: Cosine similarity score from vector search (0.0 to 1.0).
        retrieved_at: Timestamp when the document was retrieved.
    """

    title: str
    content: str
    category: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    similarity_score: float = 1.0
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate document fields after initialization."""
        if not self.title or not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.content or not self.content.strip():
            raise ValueError("content must not be empty")
        if not self.category or not self.category.strip():
            raise ValueError("category must not be empty")
        if not (0.0 <= self.similarity_score <= 1.0):
            raise ValueError("similarity_score must be between 0.0 and 1.0")

    @property
    def is_high_relevance(self) -> bool:
        """Check if the document has high relevance (similarity >= 0.7)."""
        return self.similarity_score >= 0.7

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "similarity_score": self.similarity_score,
            "retrieved_at": self.retrieved_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> RetrievedDocument:
        """Create a RetrievedDocument from a dictionary."""
        return cls(
            id=uuid.UUID(data["id"]) if isinstance(data.get("id"), str) else data.get("id", uuid.uuid4()),
            title=data["title"],
            content=data["content"],
            category=data["category"],
            similarity_score=data.get("similarity_score", 1.0),
            retrieved_at=datetime.fromisoformat(data["retrieved_at"])
            if "retrieved_at" in data
            else datetime.now(timezone.utc),
        )
