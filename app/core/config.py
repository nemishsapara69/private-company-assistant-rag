from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Private Company Assistant Using RAG"
    app_env: str = "dev"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    jwt_secret_key: str = "dev_only_change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./assistant.db"
    upload_dir: str = "uploads"
    qdrant_path: str = "qdrant_data"
    qdrant_collection: str = "company_knowledge_chunks"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.app_env.lower() != "dev" and self.jwt_secret_key == "dev_only_change_me":
            raise ValueError("Set JWT_SECRET_KEY to a non-default value outside dev environment.")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
