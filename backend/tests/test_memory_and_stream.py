"""Long-term memory CRUD and chat stream endpoint."""

from __future__ import annotations


def test_memory_crud(client) -> None:
    created = client.post(
        "/api/v1/memory",
        json={"content": "Prefer concise answers", "memory_type": "preference", "scope": "user"},
    )
    assert created.status_code == 200, created.text
    memory_id = created.json()["id"]

    listed = client.get("/api/v1/memory")
    assert listed.status_code == 200
    assert any(item["id"] == memory_id for item in listed.json()["items"])

    deleted = client.delete(f"/api/v1/memory/{memory_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"


def test_chat_stream_sse(client) -> None:
    response = client.post("/api/v1/chat/stream", json={"message": "What is Atlas?"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "data:" in body
    assert '"type": "final"' in body or '"type":"final"' in body
