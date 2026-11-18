"""Document parsers for supported Atlas formats."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader

PARSER_VERSION = "atlas-parser-v1"


@dataclass(frozen=True, slots=True)
class ParsedPage:
    page_number: int | None
    section: str | None
    text: str


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    pages: list[ParsedPage]
    parser_version: str = PARSER_VERSION

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text.strip())


def parse_bytes(*, content: bytes, mime_type: str, filename: str) -> ParsedDocument:
    lower = filename.lower()
    if mime_type == "application/pdf" or lower.endswith(".pdf"):
        return _parse_pdf(content)
    if mime_type in {"text/plain"} or lower.endswith(".txt"):
        return _parse_text(content)
    if mime_type in {"text/markdown"} or lower.endswith(".md"):
        return _parse_text(content)
    if (
        mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or lower.endswith(".docx")
    ):
        return _parse_docx(content)
    if mime_type in {"text/html", "application/xhtml+xml"} or lower.endswith((".html", ".htm")):
        return _parse_html(content)
    raise ValueError(f"Unsupported document type: {mime_type}")


def _parse_pdf(content: bytes) -> ParsedDocument:
    reader = PdfReader(io.BytesIO(content))
    pages: list[ParsedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(ParsedPage(page_number=index, section=None, text=_normalize(text)))

    if not any(page.text.strip() for page in pages):
        raise ValueError("PDF contained no extractable text")
    return ParsedDocument(pages=pages)


def _parse_text(content: bytes) -> ParsedDocument:
    text = _normalize(content.decode("utf-8", errors="replace"))

    if not text.strip():
        raise ValueError("Empty text document")
    return ParsedDocument(pages=[ParsedPage(page_number=1, section=None, text=text)])


def _parse_docx(content: bytes) -> ParsedDocument:
    document = DocxDocument(io.BytesIO(content))
    paragraphs = [_normalize(p.text) for p in document.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)

    if not text.strip():
        raise ValueError("DOCX contained no extractable text")
    return ParsedDocument(pages=[ParsedPage(page_number=1, section=None, text=text)])


def _parse_html(content: bytes) -> ParsedDocument:
    soup = BeautifulSoup(content, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = _normalize(soup.get_text("\n"))

    if not text.strip():
        raise ValueError("HTML contained no extractable text")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    return ParsedDocument(pages=[ParsedPage(page_number=1, section=title, text=text)])


def _normalize(text: str) -> str:
    # pypdf often emits NUL bytes in ligatures/invoice IDs; Postgres rejects \x00 in text.
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
