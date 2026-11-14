"""Local embedding adapter using sentence-transformers."""

from __future__ import annotations

from typing import List

from sentence_transformers import SentenceTransformer

from src.domain.agent.repository import Embedder


class LocalEmbedder(Embedder):
    """Adapter that generates embeddings using a local sentence-transformers model.

    Implements the Embedder port using a lightweight embedding model
    (all-MiniLM-L6-v2 by default: 384 dims, ~80MB, runs locally).

    Args:
        model_name: Sentence-transformers model name or path.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        """Lazy-load the embedding model on first use."""
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    async def embed(self, text: str) -> List[float]:
        """Generate embedding vector for a single text.

        Args:
            text: Text to embed.

        Returns:
            List of floats (384 dimensions for all-MiniLM-L6-v2).
        """
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def embed_many(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
