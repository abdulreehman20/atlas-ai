"""PDF/text normalization must strip Postgres-illegal NUL bytes."""

from app.ai.parsing import _normalize, parse_bytes


def test_normalize_strips_nul_bytes() -> None:
    assert "\x00" not in _normalize("54C9DAF1\x000007")
    assert _normalize("54C9DAF1\x000007") == "54C9DAF10007"


def test_parse_text_strips_nul_bytes() -> None:
    parsed = parse_bytes(
        content=b"Invoice 54C9DAF1\x000007",
        mime_type="text/plain",
        filename="note.txt",
    )
    assert "\x00" not in parsed.text
    assert "54C9DAF10007" in parsed.text
