"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Atlas backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "Atlas Enterprise AI"
    api_v1_prefix: str = "/api/v1"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    log_level: str = "INFO"

    frontend_url: str = "http://localhost:3000"

    sentry_dsn: str = ""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_jwks_url: str = ""
    supabase_storage_bucket: str = "atlas-private-documents"

    database_url: str = "sqlite://"
    migration_database_url: str = ""
    checkpoint_database_url: str = ""

    # OpenRouter (Bedrock replacement for chat + embeddings)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_chat_model: str = "nvidia/nemotron-3.5-lightning:free"
    openrouter_embedding_model: str = "nvidia/nemotron-3-embed-1b:free"
    # Nemotron 3 Embed 1B native size — Pinecone index must match.
    embedding_dimension: int = 2048

    pinecone_api_key: str = ""
    pinecone_index_name: str = "atlas-rag-index-dev"
    pinecone_index_host: str = ""
    pinecone_cloud: str = "aws"
    pinecone_region: str = ""

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "atlas-enterprise-ai-dev"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    upload_max_file_size_mb: int = 10
    rag_top_k: int = 5
    memory_max_turns: int = 6
    context_token_budget: int = 12000
    chat_max_tokens: int = 4096
    prompt_version: str = "atlas-rag-v1"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    free_member_limit: int = 3
    free_document_limit: int = 10
    free_storage_mib: int = 500
    free_chat_monthly: int = 100
    free_max_file_mib: int = 10
    pro_member_limit: int = 25
    pro_document_limit: int = 200
    pro_storage_mib: int = 20480
    pro_chat_monthly: int = 5000
    pro_max_file_mib: int = 25

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None or value == "":
            return ["http://localhost:3000"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        raise TypeError("cors_origins must be a comma-separated string or list")

    @property
    def alembic_database_url(self) -> str:
        return self.migration_database_url or self.database_url

    @property
    def effective_supabase_key(self) -> str:
        return self.supabase_service_role_key or self.supabase_secret_key

    def has_jwt_verifier(self) -> bool:
        return bool(self.supabase_jwt_secret or self.supabase_jwks_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
