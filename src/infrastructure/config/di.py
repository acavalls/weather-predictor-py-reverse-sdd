"""Dependency injection container — declarative wiring of ports to adapters.

Uses dependency-injector to define providers and their relationships.
The container is wired into FastAPI routes at startup.
"""

from __future__ import annotations

from dependency_injector import containers, providers

from src.application.ask_agent.handler import AskAgentHandler
from src.application.predict.handler import PredictHandler
from src.infrastructure.config.settings import settings
from src.infrastructure.embedding.local_embedder import LocalEmbedder
from src.infrastructure.llm import OpenCodeGoLLM
from src.infrastructure.logging import LoggingAdapter
from src.infrastructure.ml.feature_extractor import TemporalFeatureExtractor
from src.infrastructure.ml.local_predictor import LocalPredictor
from src.infrastructure.persistence.knowledge_base_adapter import KnowledgeBaseAdapter
from src.infrastructure.persistence.session import get_engine
from src.infrastructure.weather.open_meteo_adapter import OpenMeteoAdapter


class Container(containers.DeclarativeContainer):
    """Declarative DI container.

    Providers are instantiated lazily and cached as singletons.
    Dependencies are wired automatically via the provider graph.
    """

    config = providers.Configuration()

    # Driven adapters (implement domain ports)
    logger = providers.Singleton(
        LoggingAdapter,
        name="src.application",
    )

    weather_provider = providers.Singleton(
        OpenMeteoAdapter,
        base_url=settings.open_meteo_base_url,
    )

    model_predictor = providers.Singleton(
        LocalPredictor,
        default_model_path=settings.model_path,
    )

    feature_extractor = providers.Singleton(
        TemporalFeatureExtractor,
    )

    db_engine = providers.Callable(get_engine)

    vector_store = providers.Singleton(
        KnowledgeBaseAdapter,
        engine=db_engine,
    )

    embedder = providers.Singleton(
        LocalEmbedder,
    )

    llm_provider = providers.Singleton(
        OpenCodeGoLLM,
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_url,
        model=settings.llm_model,
    )

    # Use cases (driver port implementations — depend on driven adapters above)
    predict_use_case = providers.Singleton(
        PredictHandler,
        weather_provider=weather_provider,
        model_predictor=model_predictor,
        feature_extractor=feature_extractor,
        model_path=settings.model_path,
    )

    ask_agent_use_case = providers.Singleton(
        AskAgentHandler,
        logger=logger,
        weather_provider=weather_provider,
        model_predictor=model_predictor,
        feature_extractor=feature_extractor,
        vector_store=vector_store,
        embedder=embedder,
        llm_provider=llm_provider,
        model_path=settings.model_path,
    )


container = Container()
