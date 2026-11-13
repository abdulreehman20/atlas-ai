"""Document text extraction."""

from __future__ import annotations

import io
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".html", ".htm"}


# DELETE -- This is not in use. Prefer app.ai.parsing for extraction.
# SUPPORTED_EXTENSIONS above is still used by routes/documents.py.
def extract_text(*, filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")
    if suffix in {".txt", ".md"}:
        return data.decode("utf-8", errors="ignore")
    if suffix in {".html", ".htm"}:
        soup = BeautifulSoup(data, "lxml")
        return soup.get_text("\n", strip=True)
    if suffix == ".docx":
        doc = DocxDocument(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        joined = "\n".join(pages).strip()
        if not joined:
            raise ValueError("PDF has no extractable text (OCR not enabled)")
        return joined
    raise ValueError(f"Unsupported file type: {suffix}")
