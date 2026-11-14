"""AskAgent use case port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from src.application.ask_agent.command import AskAgentCommand
from src.domain.agent.events import DomainEvent


@dataclass(frozen=True)
class AskAgentResult:
    """Result of an AskAgent use case execution.

    Attributes:
        response: Natural language response from the LLM.
        session_id: Unique identifier for the chat session.
        events: Domain events produced during execution.
    """

    response: str
    session_id: str
    events: Sequence[DomainEvent]


class IAskAgentUseCase(ABC):
    """Driver port for the AskAgent use case.

    Implementations: AskAgentHandler.
    """

    @abstractmethod
    async def execute(self, command: AskAgentCommand) -> AskAgentResult:
        """Execute a conversational weather agent query.

        Orchestrates: intent classification → weather fetch → ML prediction →
        RAG retrieval → LLM prompt generation → response.

        Args:
            command: Agent query command with user's natural language text.

        Returns:
            AskAgentResult with the generated response and domain events.

        Raises:
            NotFoundError: If location or weather data cannot be resolved.
            ValueError: If the query is invalid or processing fails.
        """
        pass
