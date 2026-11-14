"""LLMProvider port interface."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Port for interacting with a Large Language Model API.

    Implementations: MockLLM, OpenCodeGoLLM.
    """

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate a response from an enriched prompt.

        The prompt should already contain all context (RAG docs, ML predictions,
        weather data) combined with the user's query. Each adapter decides how
        to format this for its underlying API (e.g., OpenAI adds a system role
        internally, Ollama passes it as plain text).

        Args:
            prompt: The complete, enriched prompt to send to the LLM.

        Returns:
            Generated response text from the LLM.
        """
        pass
