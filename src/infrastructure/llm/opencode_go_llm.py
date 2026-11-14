"""OpenCode Go LLM provider — real API adapter."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import httpx

from src.domain.agent.repository import LLMProvider

logger = logging.getLogger(__name__)


class OpenCodeGoLLM(LLMProvider):
    """LLM provider that calls the OpenCode Go API.

    Implements the LLMProvider port by sending the enriched prompt
    to the OpenCode Go API and returning the generated response.

    Attributes:
        api_key: Authentication key for the API.
        base_url: API base URL.
        model: Model identifier to use.
        timeout: Request timeout in seconds.
        session_id: Value for the mandatory x-opencode-session header.
            If not provided, a random UUID is generated per instance.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://opencode.ai/zen/go/v1",
        model: str = "mimo-v2.6-flash",
        timeout: float = 30.0,
        session_id: Optional[str] = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        # The OpenCode Go endpoint rejects requests without x-opencode-session (400 MissingSessionID).
        self._session_id = session_id or str(uuid.uuid4())

    async def generate(self, prompt: str) -> str:
        """Generate a response from the enriched prompt via OpenCode Go API.

        Args:
            prompt: Complete prompt with context (RAG docs, ML predictions, weather data).

        Returns:
            Generated response text from the LLM.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status.
            httpx.RequestError: If the request fails (network, timeout).
        """
        url = f"{self._base_url}/chat/completions"
        logger.info("LLM request: url=%s model=%s prompt_len=%d", url, self._model, len(prompt))
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "x-opencode-session": self._session_id,
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
            )
            logger.info("LLM response: status=%d body_len=%d", response.status_code, len(response.content))
            if response.status_code != 200:
                logger.error("LLM error response: %s", response.text)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("LLM content length=%d", len(content))
            return content
