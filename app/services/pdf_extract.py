"""Extract text from uploaded PDFs and plain-text files."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_file_text(path: str | Path) -> str:
    path = Path(path)
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")

    reader = PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"--- Page {i} ---\n{text.strip()}")
    return "\n\n".join(parts)


def extract_pdf_text(path: str | Path) -> str:
    return extract_file_text(path)


def extract_multiple(paths: list[str | Path]) -> str:
    chunks: list[str] = []
    for p in paths:
        name = Path(p).name
        text = extract_file_text(p)
        if text.strip():
            chunks.append(f"===== FILE: {name} =====\n{text}")
    return "\n\n".join(chunks)
