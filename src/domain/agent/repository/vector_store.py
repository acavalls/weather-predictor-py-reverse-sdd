"""VectorStore port interface."""

from abc import ABC, abstractmethod
from typing import List

from src.domain.agent.value_objects import RetrievedDocument


class VectorStore(ABC):
    """Port for storing and retrieving documents via vector similarity.

    Implementations: PgVectorAdapter, ChromaDBAdapter, InMemoryVectorStore.
    """

    @abstractmethod
    async def add_document(self, document: RetrievedDocument, embedding: List[float]) -> None:
        """Store a document with its embedding.

        Args:
            document: Document to store.
            embedding: Pre-computed embedding vector.
        """
        pass

    @abstractmethod
    async def add_documents(self, documents: List[RetrievedDocument], embeddings: List[List[float]]) -> None:
        """Store multiple documents with their embeddings.

        Args:
            documents: Documents to store.
            embeddings: Pre-computed embedding vectors, one per document.
        """
        pass

    @abstractmethod
    async def search(self, query_embedding: List[float], top_k: int = 3) -> List[RetrievedDocument]:
        """Find documents most similar to the query embedding.

        Args:
            query_embedding: Embedding vector of the search query.
            top_k: Number of results to return.

        Returns:
            List of RetrievedDocument ordered by similarity (highest first).
        """
        pass
