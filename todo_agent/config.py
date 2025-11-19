from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    tavily_api_key: str
    database_dsn: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
