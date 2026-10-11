"""Convert parsed documents and chunks to the proposed Delta table rows."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from .chunking import DocumentChunk
from .documents import DocumentRecord


def document_to_raw_row(
    document: DocumentRecord,
    *,
    retrieved_at: datetime | None,
    ingested_at: datetime,
) -> dict[str, object]:
    """Serialize a document using the ``raw_documents`` SQL column names."""
    return {
        "doc_id": document.doc_id,
        "source": document.source,
        "title": document.title,
        "url": document.url,
        "content": document.text,
        "content_sha256": _text_sha256(document.text),
        "retrieved_at": retrieved_at,
        "ingested_at": ingested_at,
    }


def chunk_to_row(chunk: DocumentChunk, *, chunked_at: datetime) -> dict[str, object]:
    """Serialize a chunk using the ``document_chunks`` SQL column names."""
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "source": chunk.source,
        "title": chunk.title,
        "url": chunk.url,
        "section": chunk.section,
        "chunk_index": chunk.chunk_index,
        "start_char": chunk.start_char,
        "end_char": chunk.end_char,
        "chunk_text": chunk.text,
        "chunk_sha256": _text_sha256(chunk.text),
        "chunked_at": chunked_at,
    }


def _text_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()
