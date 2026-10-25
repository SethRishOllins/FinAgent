from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FinAgent"
    data_mode: str = "live"
    llm_provider: str = "none"
    max_agent_iterations: int = 2
    max_tool_calls: int = 12
    max_upload_bytes: int = 10_000_000
    database_url: str = "sqlite:///./finagent.db"
    redis_url: str | None = None
    qdrant_url: str | None = None
    qdrant_collection: str = "finagent_documents"
    market_provider: str = "yfinance"
    financial_provider: str = "yfinance"
    profile_provider: str = "yfinance"
    news_provider: str = "newsapi"
    newsapi_key: str | None = None
    openai_api_key: str | None = None
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    market_cache_ttl_seconds: int = 300
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore"
    )


settings = Settings()
