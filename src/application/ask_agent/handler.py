"""AskAgent use case handler — orchestrates weather + ML + RAG + LLM."""

from __future__ import annotations

import re
from typing import List, Optional

from src.application.ask_agent.command import AskAgentCommand
from src.application.ask_agent.port import AskAgentResult, IAskAgentUseCase
from src.domain.agent.aggregate import ChatSession
from src.domain.agent.repository import Embedder, LLMProvider, VectorStore
from src.domain.agent.value_objects import ContextChunk, QueryIntent
from src.domain.ml.repository import FeatureExtractor, ModelPredictor
from src.domain.ml.value_objects import ModelMetadata
from src.domain.shared.logger import Logger
from src.domain.weather.repository import WeatherProvider


class AskAgentHandler(IAskAgentUseCase):
    """Handler that orchestrates the conversational weather agent flow.

    Injects driven ports (WeatherProvider, ModelPredictor, FeatureExtractor,
    VectorStore, Embedder, LLMProvider, Logger) and implements the driver port
    (IAskAgentUseCase).

    Flow:
        1. Create ChatSession with user query
        2. Classify query intent (forecast, advice, current, etc.)
        3. If weather-related: geocode → fetch weather → ML predict → add context
        4. RAG retrieval: embed query → search knowledge base → add context
        5. Build enriched prompt from context chunks + user query
        6. LLM generates natural language response
        7. Save response to session, collect domain events
    """

    _SYSTEM_PROMPT = (
        "You are a weather assistant. Answer the user's question using the "
        "provided context (weather data, ML predictions, and meteorological "
        "principles). Be concise, scientific, and helpful. If the context "
        "doesn't contain enough information, say so."
    )

    def __init__(
        self,
        weather_provider: WeatherProvider,
        model_predictor: ModelPredictor,
        feature_extractor: FeatureExtractor,
        vector_store: VectorStore,
        embedder: Embedder,
        llm_provider: LLMProvider,
        logger: Logger,
        model_path: str = "model.pkl",
    ) -> None:
        self._weather_provider = weather_provider
        self._model_predictor = model_predictor
        self._feature_extractor = feature_extractor
        self._vector_store = vector_store
        self._embedder = embedder
        self._llm_provider = llm_provider
        self._logger = logger
        self._model_path = model_path
        self._model: Optional[ModelMetadata] = None

    async def _ensure_model_loaded(self) -> ModelMetadata:
        """Load model on first use (lazy initialization)."""
        if self._model is None:
            self._model = await self._model_predictor.load_model(self._model_path)
        return self._model

    @staticmethod
    def _extract_city(query: str) -> Optional[str]:
        """Extract city name from user query using simple heuristics.

        Looks for patterns like "in {city}", "at {city}", "for {city}", "en {city}".
        Falls back to None if no pattern matches.

        Args:
            query: User's natural language query.

        Returns:
            Extracted city name or None.
        """
        patterns = [
            r"\bin\s+([A-ZÁÉÍÓÚÜ][a-záéíóúü]+(?:\s+[A-ZÁÉÍÓÚÜ][a-záéíóúü]+)*)\b",
            r"\bat\s+([A-ZÁÉÍÓÚÜ][a-záéíóúü]+(?:\s+[A-ZÁÉÍÓÚÜ][a-záéíóúü]+)*)\b",
            r"\bfor\s+([A-ZÁÉÍÓÚÜ][a-záéíóúü]+(?:\s+[A-ZÁÉÍÓÚÜ][a-záéíóúü]+)*)\b",
            r"\ben\s+([A-ZÁÉÍÓÚÜ][a-záéíóúü]+(?:\s+[A-ZÁÉÍÓÚÜ][a-záéíóúü]+)*)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1)
        return None

    async def execute(self, command: AskAgentCommand) -> AskAgentResult:
        """Execute the agent orchestration flow.

        Args:
            command: Agent query command with user's natural language text.

        Returns:
            AskAgentResult with the generated response and domain events.
        """
        self._logger.info("Step 1: Creating session, query=%r", command.query_text)
        # 1. Create session and classify intent
        session = ChatSession(query_text=command.query_text)
        intent = QueryIntent.from_query(command.query_text)
        self._logger.info("Intent: is_weather=%s", intent.is_weather_related)

        # 2. If weather-related, gather context
        if intent.is_weather_related:
            city = self._extract_city(command.query_text)
            self._logger.info("Step 2: City extracted=%r", city)
            if city:
                await self._gather_weather_context(session, city)
                self._logger.info("Step 2: Weather context gathered, chunks=%d", len(session.context_chunks))

        # 3. RAG retrieval (always, for any weather-related or general query)
        self._logger.info("Step 3: Gathering RAG context")
        await self._gather_rag_context(session, command.query_text)
        self._logger.info("Step 3: RAG context gathered, chunks=%d", len(session.context_chunks))

        # 4. Build prompt and call LLM
        self._logger.info("Step 4: Building prompt")
        prompt = self._build_prompt(session, command.query_text)
        self._logger.info("Step 4: Prompt length=%d chars", len(prompt))
        self._logger.info("Full prompt:\n%s", prompt)
        self._logger.info("Step 4: Calling LLM")
        response = await self._llm_provider.generate(prompt)
        self._logger.info("Step 4: LLM response received, length=%d", len(response))

        # 5. Save response and collect events
        session.generate_response(response)
        events = session.pop_events()
        self._logger.info("Step 5: Complete, events=%d", len(events))

        return AskAgentResult(
            response=response,
            session_id=str(session.id),
            events=events,
        )

    async def _gather_weather_context(self, session: ChatSession, city: str) -> None:
        """Fetch weather data and ML predictions, add as context chunks.

        Args:
            session: Chat session to add context to.
            city: City name to fetch weather for.
        """
        # Geocode and fetch weather
        location = await self._weather_provider.geocode(city)
        current_weather = await self._weather_provider.get_current_weather(location)

        # ML prediction
        model = await self._ensure_model_loaded()
        feature_set = await self._feature_extractor.extract(
            current_conditions=current_weather.to_features(),
            city=location.name or city,
            timestamp=session.created_at,
            horizons=[6, 12, 24],
        )
        prediction_result = await self._model_predictor.predict(
            model=model,
            feature_set=feature_set,
            horizons=[6, 12, 24],
        )

        # Add weather context chunk
        weather_summary = self._format_weather_summary(current_weather, prediction_result)
        self._logger.info("Weather summary:\n%s", weather_summary)
        session.add_context(
            ContextChunk(
                chunk_type="weather_and_prediction",
                content=weather_summary,
                source="open_meteo_and_ml",
                metadata={
                    "city": location.name or city,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                },
            )
        )

    async def _gather_rag_context(self, session: ChatSession, query: str) -> None:
        """Retrieve relevant meteorological documents from knowledge base.

        Args:
            session: Chat session to add context to.
            query: User query to search for.
        """
        query_embedding = await self._embedder.embed(query)
        documents = await self._vector_store.search(query_embedding, top_k=3)
        if documents:
            self._logger.info("RAG retrieved %d documents", len(documents))
            for i, doc in enumerate(documents):
                self._logger.info(
                    "RAG doc %d: title=%r score=%.3f content_preview=%.200s",
                    i,
                    doc.title,
                    doc.similarity_score,
                    doc.content,
                )
            session.add_rag_documents(documents)
        else:
            self._logger.info("RAG: no documents retrieved")

    @staticmethod
    def _build_prompt(session: ChatSession, user_query: str) -> str:
        """Build the enriched prompt for the LLM.

        Combines system instructions, context chunks, and the user query
        into a single prompt string.

        Args:
            session: Chat session with accumulated context.
            user_query: Original user query text.

        Returns:
            Complete prompt string ready for LLM generation.
        """
        parts: List[str] = [AskAgentHandler._SYSTEM_PROMPT, ""]

        if session.context_chunks:
            parts.append("## Context")
            parts.append("")
            for chunk in session.context_chunks:
                parts.append(f"### {chunk.chunk_type} (source: {chunk.source})")
                parts.append(chunk.content)
                parts.append("")

        parts.append("## User Query")
        parts.append("")
        parts.append(user_query)

        return "\n".join(parts)

    @staticmethod
    def _format_weather_summary(current_weather, prediction_result) -> str:
        """Format current weather and ML predictions into a readable summary.

        Args:
            current_weather: CurrentWeather domain object.
            prediction_result: PredictionResult from ModelPredictor.

        Returns:
            Formatted string with current conditions and predictions.
        """
        lines = [
            f"Current conditions: temp={current_weather.temperature.value}°C, "
            f"humidity={current_weather.humidity.value}%, "
            f"pressure={current_weather.pressure.value}hPa, "
            f"wind={current_weather.wind_speed.value}km/h, "
            f"cloud_cover={current_weather.cloud_cover.value}%, "
            f"precipitation={current_weather.precipitation.value}mm",
            "",
            "ML Predictions:",
        ]

        for horizon, values in prediction_result.predictions.items():
            lines.append(
                f"  {horizon}h: temp={values.get('temperature_2m', 'N/A')}°C, "
                f"humidity={values.get('relative_humidity_2m', 'N/A')}%, "
                f"pressure={values.get('surface_pressure', 'N/A')}hPa"
            )

        return "\n".join(lines)
