"""LLM infrastructure adapters."""

from .mock_llm import MockLLM
from .opencode_go_llm import OpenCodeGoLLM

__all__ = ["MockLLM", "OpenCodeGoLLM"]
