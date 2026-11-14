"""ChatSession aggregate root for the agent domain."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from src.domain.agent.events import QueryReceived, ResponseGenerated
from src.domain.agent.value_objects import ContextChunk, RetrievedDocument


@dataclass
class ChatSession:
    """Aggregate root for a conversational weather agent session.

    Tracks the lifecycle of a user interaction: receiving queries, gathering
    context (weather data, ML predictions, RAG documents), and generating
    responses. Collects domain events as state changes occur.

    Attributes:
        id: Unique session identifier.
        created_at: When the session was created.
        query_text: The user's query text.
        response_text: The generated response (None until generated).
        context_chunks: Context gathered during response generation.
        _events: Collected domain events (internal).
    """

    query_text: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response_text: str | None = None
    context_chunks: List[ContextChunk] = field(default_factory=list)
    _events: List[QueryReceived | ResponseGenerated] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Record initial query received event."""
        if not self.query_text or not self.query_text.strip():
            raise ValueError("query_text must not be empty")
        self._record_event(
            QueryReceived(
                session_id=str(self.id),
                query_text=self.query_text,
            )
        )

    @property
    def is_responded(self) -> bool:
        """Whether a response has been generated for this session."""
        return self.response_text is not None

    def add_context(self, chunk: ContextChunk) -> None:
        """Add a context chunk to the session.

        Args:
            chunk: Context chunk to add (weather data, ML prediction, RAG doc, etc.).

        Raises:
            ValueError: If the session already has a response.
        """
        if self.is_responded:
            raise ValueError("Cannot add context after response is generated")
        self.context_chunks.append(chunk)

    def add_rag_documents(self, documents: List[RetrievedDocument]) -> None:
        """Add RAG-retrieved documents as context chunks.

        Args:
            documents: List of retrieved documents from the knowledge base.

        Raises:
            ValueError: If the session already has a response.
        """
        if self.is_responded:
            raise ValueError("Cannot add context after response is generated")
        for doc in documents:
            chunk = ContextChunk(
                chunk_type="rag_document",
                content=doc.content,
                source="knowledge_base",
                metadata={
                    "title": doc.title,
                    "category": doc.category,
                    "similarity_score": doc.similarity_score,
                },
            )
            self.context_chunks.append(chunk)

    def generate_response(self, response: str) -> None:
        """Complete the session with a generated response.

        Args:
            response: Natural language response text to the user's query.

        Raises:
            ValueError: If the response has already been generated.
        """
        if self.is_responded:
            raise ValueError("Response has already been generated")

        self.response_text = response

        rag_docs = [c for c in self.context_chunks if c.chunk_type == "rag_document"]
        ml_predictions = [c for c in self.context_chunks if c.chunk_type == "ml_prediction"]

        self._record_event(
            ResponseGenerated(
                session_id=str(self.id),
                response_text=response,
                used_rag=len(rag_docs) > 0,
                used_ml_prediction=len(ml_predictions) > 0,
                retrieved_doc_count=len(rag_docs),
            )
        )

    def pop_events(self) -> List[QueryReceived | ResponseGenerated]:
        """Return and clear collected domain events."""
        events = list(self._events)
        self._events.clear()
        return events

    def _record_event(self, event: QueryReceived | ResponseGenerated) -> None:
        """Add a domain event to the internal collection."""
        self._events.append(event)

    def get_context_summary(self) -> str:
        """Return a summary of all context gathered for this session.

        Returns:
            String summary of context chunks by type.

        Raises:
            ValueError: If no context has been added.
        """
        if not self.context_chunks:
            raise ValueError("No context available for this session")

        parts: List[str] = []
        by_type: dict = {}
        for chunk in self.context_chunks:
            by_type.setdefault(chunk.chunk_type, []).append(chunk)

        for chunk_type, chunks in by_type.items():
            parts.append(f"{chunk_type}: {len(chunks)} item(s)")
            for chunk in chunks:
                preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
                parts.append(f"  [{chunk.source}] {preview}")

        return "\n".join(parts)
