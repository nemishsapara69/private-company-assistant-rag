from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Private Company Assistant Using RAG"
    app_env: str = "dev"
    api_v1_prefix: str = "/api/v1"

    jwt_secret_key: str = "change_this_secret_in_real_project"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./assistant.db"
    upload_dir: str = "uploads"
    qdrant_path: str = "qdrant_data"
    qdrant_collection: str = "company_knowledge_chunks"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
