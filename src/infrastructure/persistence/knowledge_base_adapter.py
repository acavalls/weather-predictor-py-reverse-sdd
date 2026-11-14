"""Knowledge base adapter using SQLAlchemy async + pgvector for vector similarity search."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from src.domain.agent.repository import VectorStore
from src.domain.agent.value_objects import RetrievedDocument
from src.infrastructure.persistence.models.knowledge_base import KnowledgeBaseModel


class KnowledgeBaseAdapter(VectorStore):
    """Adapter that stores and retrieves documents via pgvector cosine similarity.

    Implements the VectorStore port using SQLAlchemy async with PostgreSQL pgvector.

    Args:
        engine: Async SQLAlchemy engine.
        table_name: Table name for the knowledge base (default: knowledge_base).
    """

    def __init__(
        self,
        engine: AsyncEngine,
        table_name: str = "knowledge_base",
    ) -> None:
        self._engine = engine
        self._table_name = table_name
        self._session_factory = async_sessionmaker(
            engine,
            expire_on_commit=False,
        )

    async def add_document(self, document: RetrievedDocument, embedding: List[float]) -> None:
        """Store a document with its embedding."""
        async with self._session_factory() as session:
            async with session.begin():
                record = KnowledgeBaseModel(
                    id=document.id,
                    title=document.title,
                    content=document.content,
                    category=document.category,
                    embedding=embedding,
                )
                await session.merge(record)

    async def add_documents(self, documents: List[RetrievedDocument], embeddings: List[List[float]]) -> None:
        """Store multiple documents with their embeddings."""
        if len(documents) != len(embeddings):
            raise ValueError("documents and embeddings must have the same length")

        async with self._session_factory() as session:
            async with session.begin():
                for doc, emb in zip(documents, embeddings):
                    record = KnowledgeBaseModel(
                        id=doc.id,
                        title=doc.title,
                        content=doc.content,
                        category=doc.category,
                        embedding=emb,
                    )
                    await session.merge(record)

    async def search(self, query_embedding: List[float], top_k: int = 3) -> List[RetrievedDocument]:
        """Find documents most similar to the query embedding using cosine similarity."""
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        sql = text(f"""
            SELECT id, title, content, category,
                   1 - (embedding <=> CAST(:embedding AS vector))::float AS similarity
            FROM {self._table_name}
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)

        async with self._session_factory() as session:
            result = await session.stream(sql, {"embedding": embedding_str, "limit": top_k})
            rows = [row async for row in result]

        documents: List[RetrievedDocument] = []
        for row in rows:
            doc_id = row[0]
            if isinstance(doc_id, str):
                doc_id = uuid.UUID(doc_id)
            documents.append(
                RetrievedDocument(
                    id=doc_id,
                    title=row[1],
                    content=row[2],
                    category=row[3],
                    similarity_score=float(row[4]),
                    retrieved_at=datetime.now(timezone.utc),
                )
            )
        return documents
