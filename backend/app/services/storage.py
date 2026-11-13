"""Supabase Storage helpers (service-role)."""

from __future__ import annotations

from typing import Any, Protocol

from supabase import create_client

from app.core.config import Settings


class StorageClient(Protocol):
    def download(self, path: str) -> bytes: ...

    def object_exists(self, path: str) -> bool: ...


class SupabaseStorageClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any | None = None

    def _ensure(self) -> Any:
        if self._client is not None:
            return self._client
        key = self._settings.effective_supabase_key
        self._client = create_client(self._settings.supabase_url, key)
        return self._client

    def download(self, path: str) -> bytes:
        client = self._ensure()
        bucket = self._settings.supabase_storage_bucket
        response = client.storage.from_(bucket).download(path)
        return bytes(response)

    def object_exists(self, path: str) -> bool:
        try:
            self.download(path)
            return True
        except Exception:
            return False


class InMemoryStorageClient:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = objects or {}

    def download(self, path: str) -> bytes:
        if path not in self.objects:
            raise FileNotFoundError(path)
        return self.objects[path]

    def object_exists(self, path: str) -> bool:
        return path in self.objects
