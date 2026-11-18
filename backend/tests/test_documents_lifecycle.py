"""Document upload verification, reprocess, and delete cleanup."""

from __future__ import annotations

import hashlib

from app.ai.vector_store import InMemoryVectorStore
from app.api.deps import get_storage_client, get_vector_store
from app.services.storage import InMemoryStorageClient


def test_upload_complete_verifies_object_and_reprocess_delete(client, principal) -> None:
    storage = InMemoryStorageClient()
    vectors = InMemoryVectorStore()
    client.app.dependency_overrides[get_storage_client] = lambda: storage
    client.app.dependency_overrides[get_vector_store] = lambda: vectors

    created = client.post(
        "/api/v1/documents",
        json={"filename": "note.txt", "size_bytes": 5, "mime_type": "text/plain"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    doc_id = body["id"]
    path = body["storage_path"]

    missing = client.post(
        f"/api/v1/documents/{doc_id}/upload-complete",
        json={"storage_path": path},
    )
    assert missing.status_code == 404

    content = b"hello"
    storage.objects[path] = content
    digest = hashlib.sha256(content).hexdigest()
    done = client.post(
        f"/api/v1/documents/{doc_id}/upload-complete",
        json={"storage_path": path, "checksum": digest},
    )
    assert done.status_code == 200, done.text
    assert done.json()["job_id"]

    reprocess = client.post(f"/api/v1/documents/{doc_id}/reprocess")
    assert reprocess.status_code == 200, reprocess.text

    vectors.upsert(
        workspace_id=principal.workspace_id,
        vectors=[("chunk-1", [0.1] * 8, {"document_id": doc_id})],
    )
    deleted = client.delete(f"/api/v1/documents/{doc_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert path not in storage.objects
