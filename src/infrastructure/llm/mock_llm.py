"""Mock LLM provider — deterministic responses for testing and development."""

from __future__ import annotations

from src.domain.agent.repository import LLMProvider


class MockLLM(LLMProvider):
    """Deterministic LLM provider that returns pre-configured responses.

    Useful for testing the agent orchestration flow without calling a real LLM API.
    Supports two modes:
    - Fixed response: always returns the same text.
    - Echo mode: returns the input prompt as-is.

    Attributes:
        response: Fixed response text (used when echo_mode is False).
        echo_mode: When True, returns the input prompt instead of fixed response.
        call_count: Number of times generate() was called.
        last_prompt: The last prompt string passed to generate().
    """

    def __init__(self, response: str = "Mock LLM response.", echo_mode: bool = False) -> None:
        self.response = response
        self.echo_mode = echo_mode
        self.call_count = 0
        self.last_prompt: str = ""

    async def generate(self, prompt: str) -> str:
        """Return fixed or echo response, tracking the call.

        Args:
            prompt: Enriched prompt text (ignored in fixed mode, returned in echo mode).

        Returns:
            Pre-configured response text or the input prompt in echo mode.
        """
        self.call_count += 1
        self.last_prompt = prompt

        if self.echo_mode:
            return prompt

        return self.response
