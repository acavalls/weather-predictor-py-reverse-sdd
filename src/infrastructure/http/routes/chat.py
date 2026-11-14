"""Chat route — POST /chat endpoint for conversational weather agent."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.ask_agent.command import AskAgentCommand
from src.application.ask_agent.port import IAskAgentUseCase
from src.domain.shared.errors import NotFoundError
from src.infrastructure.config.di import container

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Request body for POST /chat.

    Attributes:
        query: User's natural language weather query.
    """

    query: str = Field(..., min_length=1, description="Natural language weather query")


class ChatResponse(BaseModel):
    """Response body for POST /chat.

    Attributes:
        response: Natural language response from the agent.
        session_id: Unique identifier for the chat session.
    """

    response: str
    session_id: str


def get_ask_agent_use_case() -> IAskAgentUseCase:
    """Dependency factory — resolves AskAgentUseCase from DI container."""
    return container.ask_agent_use_case()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the weather agent a question",
    description="Get a natural language weather response with ML predictions and scientific grounding.",
)
async def chat(
    request: ChatRequest,
    use_case: IAskAgentUseCase = Depends(get_ask_agent_use_case),
) -> ChatResponse:
    """Handle POST /chat requests.

    Adapts HTTP request → AskAgentCommand → use case → HTTP response.
    """
    logger.info("Received chat request: query=%r", request.query)
    try:
        command = AskAgentCommand(query_text=request.query)
        result = await use_case.execute(command)
        logger.info("Chat request succeeded: session_id=%s", result.session_id)
    except NotFoundError as exc:
        logger.error("Chat request not found: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        logger.error("Chat request value error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Chat request unexpected error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        response=result.response,
        session_id=result.session_id,
    )
