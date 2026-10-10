from datetime import datetime, timezone
from hashlib import sha256

from src.lab12_rag.chunking import DocumentChunk
from src.lab12_rag.documents import DocumentRecord
from src.lab12_rag.table_rows import chunk_to_row, document_to_raw_row


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def test_document_row_maps_schema_fields_hash_and_injected_timestamps():
    document = DocumentRecord(
        doc_id="doc-unchanged",
        source="Python documentation",
        title="JSON Guide",
        url="https://docs.python.org/3/library/json.html",
        text="Normalized document text.",
        sections=(),
    )
    retrieved_at = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    ingested_at = datetime(2026, 1, 2, 3, 5, tzinfo=timezone.utc)

    row = document_to_raw_row(
        document,
        retrieved_at=retrieved_at,
        ingested_at=ingested_at,
    )

    assert row == {
        "doc_id": "doc-unchanged",
        "source": "Python documentation",
        "title": "JSON Guide",
        "url": "https://docs.python.org/3/library/json.html",
        "content": "Normalized document text.",
        "content_sha256": _digest("Normalized document text."),
        "retrieved_at": retrieved_at,
        "ingested_at": ingested_at,
    }


def test_chunk_row_maps_schema_fields_hash_and_injected_timestamp():
    chunk = DocumentChunk(
        chunk_id="stable-chunk-id",
        doc_id="stable-doc-id",
        source="Python documentation",
        title="JSON Guide",
        url="https://docs.python.org/3/library/json.html",
        section="Encoding",
        chunk_index=3,
        start_char=25,
        end_char=43,
        text="JSON chunk content",
    )
    chunked_at = datetime(2026, 1, 2, 3, 6, tzinfo=timezone.utc)

    row = chunk_to_row(chunk, chunked_at=chunked_at)

    assert row == {
        "chunk_id": "stable-chunk-id",
        "doc_id": "stable-doc-id",
        "source": "Python documentation",
        "title": "JSON Guide",
        "url": "https://docs.python.org/3/library/json.html",
        "section": "Encoding",
        "chunk_index": 3,
        "start_char": 25,
        "end_char": 43,
        "chunk_text": "JSON chunk content",
        "chunk_sha256": _digest("JSON chunk content"),
        "chunked_at": chunked_at,
    }


def test_nullable_section_and_empty_text_are_serialized_and_hashed():
    empty_document = DocumentRecord(
        doc_id="empty-doc",
        source="Python documentation",
        title="Empty page",
        url="https://docs.python.org/empty.html",
        text="",
        sections=(),
    )
    empty_chunk = DocumentChunk(
        chunk_id="empty-chunk",
        doc_id="empty-doc",
        source="Python documentation",
        title="Empty page",
        url="https://docs.python.org/empty.html",
        section=None,
        chunk_index=0,
        start_char=0,
        end_char=0,
        text="",
    )
    timestamp = datetime(2026, 1, 2, tzinfo=timezone.utc)

    document_row = document_to_raw_row(
        empty_document,
        retrieved_at=None,
        ingested_at=timestamp,
    )
    chunk_row = chunk_to_row(empty_chunk, chunked_at=timestamp)

    assert document_row["content"] == ""
    assert document_row["content_sha256"] == _digest("")
    assert document_row["retrieved_at"] is None
    assert chunk_row["section"] is None
    assert chunk_row["chunk_text"] == ""
    assert chunk_row["chunk_sha256"] == _digest("")
