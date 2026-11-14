"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized configuration from environment variables."""

    database_url: str = "postgresql+asyncpg://weather:weather@localhost:5432/weather_agent"
    llm_api_key: str = ""
    llm_api_url: str = "https://opencode.ai/zen/go/v1"
    llm_model: str = "mimo-v2.6-flash"
    open_meteo_base_url: str = "https://api.open-meteo.com"
    model_path: str = "models/model.pkl"
    embedder_model: str = "all-MiniLM-L6-v2"
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
