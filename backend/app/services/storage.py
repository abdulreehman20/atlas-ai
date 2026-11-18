"""Supabase Storage helpers (service-role)."""

from __future__ import annotations

from typing import Any, Protocol

from supabase import create_client

from app.core.config import Settings


class StorageClient(Protocol):
    def download(self, path: str) -> bytes: ...

    def object_exists(self, path: str) -> bool: ...

    def delete(self, path: str) -> None: ...

    def create_signed_url(self, path: str, *, expires_in: int = 3600) -> str: ...

    def create_signed_upload(self, path: str, *, expires_in: int = 3600) -> dict[str, str]: ...

    def upload(self, path: str, content: bytes, *, content_type: str) -> None: ...


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

    def delete(self, path: str) -> None:
        client = self._ensure()
        bucket = self._settings.supabase_storage_bucket
        client.storage.from_(bucket).remove([path])

    def create_signed_url(self, path: str, *, expires_in: int = 3600) -> str:
        client = self._ensure()
        bucket = self._settings.supabase_storage_bucket
        response = client.storage.from_(bucket).create_signed_url(path, expires_in)
        if isinstance(response, dict):
            url = response.get("signedURL") or response.get("signedUrl") or response.get("signed_url")
            if url:
                return str(url)
        signed = getattr(response, "signed_url", None) or getattr(response, "signedURL", None)
        if signed:
            return str(signed)
        raise FileNotFoundError(path)

    def create_signed_upload(self, path: str, *, expires_in: int = 3600) -> dict[str, str]:
        _ = expires_in
        client = self._ensure()
        bucket = self._settings.supabase_storage_bucket
        response = client.storage.from_(bucket).create_signed_upload_url(path)
        if not isinstance(response, dict):
            raise RuntimeError("Unexpected signed upload response")
        token = str(response.get("token") or "")
        signed_url = str(
            response.get("signed_url")
            or response.get("signedUrl")
            or response.get("signedURL")
            or ""
        )
        if not token or not signed_url:
            raise RuntimeError("Signed upload URL missing token")
        return {"path": path, "token": token, "signed_url": signed_url}

    def upload(self, path: str, content: bytes, *, content_type: str) -> None:
        client = self._ensure()
        bucket = self._settings.supabase_storage_bucket
        client.storage.from_(bucket).upload(
            path,
            content,
            file_options={"content-type": content_type, "upsert": "true"},
        )


class InMemoryStorageClient:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = objects or {}

    def download(self, path: str) -> bytes:
        if path not in self.objects:
            raise FileNotFoundError(path)
        return self.objects[path]

    def object_exists(self, path: str) -> bool:
        return path in self.objects

    def delete(self, path: str) -> None:
        self.objects.pop(path, None)

    def create_signed_url(self, path: str, *, expires_in: int = 3600) -> str:
        _ = expires_in
        if path not in self.objects:
            raise FileNotFoundError(path)
        return f"memory://{path}"

    def create_signed_upload(self, path: str, *, expires_in: int = 3600) -> dict[str, str]:
        _ = expires_in
        return {
            "path": path,
            "token": "memory-token",
            "signed_url": f"memory-upload://{path}",
        }

    def upload(self, path: str, content: bytes, *, content_type: str) -> None:
        _ = content_type
        self.objects[path] = content
