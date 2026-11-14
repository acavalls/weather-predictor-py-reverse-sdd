"""FastAPI application entry point.

Registers routers at startup. DI container lives in src.infrastructure.config.di.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.infrastructure.http.routes.chat import router as chat_router
from src.infrastructure.http.routes.health import router as health_router
from src.infrastructure.http.routes.predict import router as predict_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="Weather Prediction Agent",
    description="Conversational weather agent with ML + RAG",
    version="0.1.0",
)

app.include_router(health_router, tags=["health"])
app.include_router(predict_router, tags=["predict"])
app.include_router(chat_router, tags=["chat"])

_HTML_CACHE: Optional[str] = None


def _get_chat_html() -> str:
    """Load chat.html once and cache it in memory."""
    global _HTML_CACHE
    if _HTML_CACHE is None:
        _HTML_CACHE = (
            Path(__file__).parent.joinpath("infrastructure", "http", "static", "chat.html").read_text(encoding="utf-8")
        )
    return _HTML_CACHE


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def chat_ui() -> HTMLResponse:
    """Serve the ChatGPT-style weather agent UI."""
    return HTMLResponse(_get_chat_html())
