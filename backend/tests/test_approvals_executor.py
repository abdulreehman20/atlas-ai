"""HITL approval executes allowlisted noop tool."""

from __future__ import annotations


def test_approve_noop_executes(client) -> None:
    created = client.post(
        "/api/v1/approvals",
        json={
            "action": "test",
            "tool_name": "noop",
            "summary": "No-op tool for unit test",
            "sanitized_arguments": {},
        },
    )
    assert created.status_code == 200, created.text
    approval_id = created.json()["id"]

    decided = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approve"},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "executed"
