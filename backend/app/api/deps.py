"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.ai.chat_model import ChatModelClient, OpenRouterChatClient, StubChatClient
from app.ai.embeddings import EmbeddingClient, OpenRouterEmbeddingClient, StubEmbeddingClient
from app.ai.vector_store import InMemoryVectorStore, PineconeVectorStore, VectorStoreClient
from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import JWTVerifier, Principal
from app.db.session import get_session
from app.services.auth import resolve_principal
from app.services.storage import InMemoryStorageClient, StorageClient, SupabaseStorageClient

bearer_scheme = HTTPBearer(auto_error=False)


def settings_dep() -> Settings:
    return get_settings()


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(settings_dep)]


def get_current_principal(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Bearer token required")
    verifier = JWTVerifier(settings)
    user = verifier.verify(credentials.credentials)
    request_id = getattr(request.state, "request_id", None)
    return resolve_principal(session, user=user, request_id=request_id, bootstrap=True)


PrincipalDep = Annotated[Principal, Depends(get_current_principal)]


def get_embedding_client(settings: SettingsDep) -> EmbeddingClient:
    if settings.app_env == "test" or not settings.openrouter_api_key:
        return StubEmbeddingClient(dimension=settings.embedding_dimension)
    return OpenRouterEmbeddingClient(settings)


def get_vector_store(settings: SettingsDep) -> VectorStoreClient:
    if settings.app_env == "test" or not settings.pinecone_api_key:
        return InMemoryVectorStore()
    return PineconeVectorStore(settings)


def get_storage_client(settings: SettingsDep) -> StorageClient:
    if settings.app_env == "test" or not settings.effective_supabase_key:
        return InMemoryStorageClient()
    return SupabaseStorageClient(settings)


def get_chat_client(settings: SettingsDep) -> ChatModelClient:
    if settings.app_env == "test" or not settings.openrouter_api_key:
        return StubChatClient()
    return OpenRouterChatClient(settings)


EmbeddingClientDep = Annotated[EmbeddingClient, Depends(get_embedding_client)]
VectorStoreDep = Annotated[VectorStoreClient, Depends(get_vector_store)]
StorageClientDep = Annotated[StorageClient, Depends(get_storage_client)]
ChatClientDep = Annotated[ChatModelClient, Depends(get_chat_client)]


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


RequestIdDep = Annotated[str | None, Depends(get_request_id)]
