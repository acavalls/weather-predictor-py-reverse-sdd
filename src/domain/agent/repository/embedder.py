"""Embedder port interface."""

from abc import ABC, abstractmethod
from typing import List


class Embedder(ABC):
    """Port for generating text embeddings (vector representations).

    Implementations: LocalEmbedder (sentence-transformers), RemoteEmbedder (API).
    """

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding vector for a single text.

        Args:
            text: Text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        pass

    @abstractmethod
    async def embed_many(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        pass
