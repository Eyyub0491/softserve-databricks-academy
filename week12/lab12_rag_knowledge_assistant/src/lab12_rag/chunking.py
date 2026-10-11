"""Deterministic character chunking with source metadata and stable IDs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from .documents import DocumentRecord, clean_text


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    doc_id: str
    source: str
    title: str
    url: str
    section: str | None
    chunk_index: int
    start_char: int
    end_char: int
    text: str


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[tuple[str, int, int]]:
    """Return normalized chunks and their half-open offsets in normalized text."""
    _validate_chunk_settings(chunk_size, overlap)
    normalized = clean_text(text)
    if not normalized:
        return []

    stride = chunk_size - overlap
    chunks: list[tuple[str, int, int]] = []
    for start in range(0, len(normalized), stride):
        end = min(start + chunk_size, len(normalized))
        piece = normalized[start:end].strip()
        if piece:
            left_trim = len(normalized[start:end]) - len(normalized[start:end].lstrip())
            right_trim = len(normalized[start:end]) - len(normalized[start:end].rstrip())
            chunks.append((piece, start + left_trim, end - right_trim))
        if end == len(normalized):
            break
    return chunks


def chunk_document(
    document: DocumentRecord,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """Chunk each parsed section while retaining document and section metadata."""
    _validate_chunk_settings(chunk_size, overlap)
    chunks: list[DocumentChunk] = []
    for section_number, section in enumerate(document.sections):
        for text, start_char, end_char in chunk_text(section.text, chunk_size, overlap):
            index = len(chunks)
            identity = "\0".join(
                (
                    document.url,
                    str(section_number),
                    str(start_char),
                    str(end_char),
                    text,
                )
            )
            chunk_id = sha256(identity.encode("utf-8")).hexdigest()
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=document.doc_id,
                    source=document.source,
                    title=document.title,
                    url=document.url,
                    section=section.title,
                    chunk_index=index,
                    start_char=start_char,
                    end_char=end_char,
                    text=text,
                )
            )
    return chunks


def _validate_chunk_settings(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap must not be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
