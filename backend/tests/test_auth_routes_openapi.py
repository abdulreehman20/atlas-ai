"""Auth routes appear in OpenAPI and reject unconfigured calls cleanly."""

from __future__ import annotations


def test_auth_routes_listed_in_openapi(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/auth/signup" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/user" in paths
    assert "/api/v1/chat/stream" in paths
    assert "/api/v1/memory" in paths
    assert "/api/v1/documents/{document_id}/reprocess" in paths


def test_login_with_bad_credentials_or_missing_config(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "secret12"},
    )
    # 503 when Supabase env is missing; 400/401 when GoTrue rejects credentials.
    assert response.status_code in {400, 401, 503}
