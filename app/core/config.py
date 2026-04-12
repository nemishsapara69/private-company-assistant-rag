from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Private Company Assistant Using RAG"
    app_env: str = "dev"
    api_v1_prefix: str = "/api/v1"

    jwt_secret_key: str = "change_this_secret_in_real_project"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./assistant.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
