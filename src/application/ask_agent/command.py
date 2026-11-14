"""AskAgent command DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AskAgentCommand:
    """Command to request a conversational weather agent response.

    Attributes:
        query_text: User's natural language query.
    """

    query_text: str

    def __post_init__(self) -> None:
        """Validate command fields."""
        if not self.query_text or not self.query_text.strip():
            raise ValueError("query_text must not be empty")
