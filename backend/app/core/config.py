from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FinAgent"
    llm_provider: str = "none"
    max_agent_iterations: int = 2
    max_tool_calls: int = 12
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


settings = Settings()
