"""Knowledge base ORM model for RAG documents with pgvector embeddings."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from src.infrastructure.persistence.models.base import Base

EMBEDDING_DIM = 384


class KnowledgeBaseModel(Base):
    """Meteorological document with vector embedding for semantic search."""

    __tablename__ = "knowledge_base"
    __table_args__ = (Index("idx_knowledge_base_category", "category"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    embedding: list[float] | None = Column(Vector(EMBEDDING_DIM), nullable=True)  # type: ignore[assignment]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<KnowledgeBaseModel(id={self.id}, title={self.title!r}, category={self.category!r})>"
