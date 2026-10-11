from datetime import datetime, timezone
from hashlib import sha256

import pytest

from src.lab12_rag.ingestion import IngestionFailure, PreparedIngestion
from src.lab12_rag.reconciliation import plan_reconciliation


URL = "https://docs.python.org/3/library/json.html"
STAMP = datetime(2026, 3, 1, tzinfo=timezone.utc)


def _digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _doc_row(content="current document", *, doc_id="doc-1", url=URL, ingested_at=STAMP):
    return {
        "doc_id": doc_id,
        "source": "Python documentation",
        "title": "Python docs",
        "url": url,
        "content": content,
        "content_sha256": _digest(content),
        "retrieved_at": STAMP,
        "ingested_at": ingested_at,
    }


def _chunk_row(
    chunk_id="chunk-1", text="current chunk", *, doc_id="doc-1", url=URL, chunked_at=STAMP
):
    return {
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "source": "Python documentation",
        "title": "Python docs",
        "url": url,
        "section": "Examples",
        "chunk_index": 0,
        "start_char": 0,
        "end_char": len(text),
        "chunk_text": text,
        "chunk_sha256": _digest(text),
        "chunked_at": chunked_at,
    }


def _result(documents=(), chunks=(), failures=()):
    return PreparedIngestion(tuple(documents), tuple(chunks), tuple(failures))


def test_unchanged_document_and_chunks_need_no_upserts_or_deletions():
    current_doc = _doc_row()
    current_chunk = _chunk_row()
    persisted_doc = {**current_doc, "retrieved_at": None, "ingested_at": datetime(2025, 1, 1, tzinfo=timezone.utc)}
    persisted_chunk = {**current_chunk, "chunked_at": datetime(2025, 1, 1, tzinfo=timezone.utc)}

    plan = plan_reconciliation(
        _result([current_doc], [current_chunk]),
        existing_document_rows=[persisted_doc],
        existing_chunk_rows=[persisted_chunk],
    )

    assert plan.raw_document_upserts == ()
    assert plan.chunk_upserts == ()
    assert plan.obsolete_chunk_ids == ()
    assert plan.empty_document_ids == ()


def test_changed_content_upserts_by_stable_doc_id_and_chunk_id():
    old_doc = _doc_row("old document")
    new_doc = _doc_row("updated document")
    old_chunk = _chunk_row("old-chunk", "old chunk")
    new_chunk = _chunk_row("new-chunk", "new chunk")

    plan = plan_reconciliation(
        _result([new_doc], [new_chunk]),
        existing_document_rows=[old_doc],
        existing_chunk_rows=[old_chunk],
    )

    assert plan.raw_document_upserts == (new_doc,)
    assert plan.chunk_upserts == (new_chunk,)
    assert plan.obsolete_chunk_ids == ("old-chunk",)
    assert plan.obsolete_chunk_urls == (("old-chunk", URL),)


def test_removed_chunks_are_deleted_for_a_successfully_processed_document():
    current_doc = _doc_row()
    retained = _chunk_row("retained", "current chunk")
    removed = _chunk_row("removed", "old content")

    plan = plan_reconciliation(
        _result([current_doc], [retained]),
        existing_document_rows=[current_doc],
        existing_chunk_rows=[retained, removed],
    )

    assert plan.obsolete_chunk_ids == ("removed",)


def test_empty_document_is_explicit_and_all_old_chunks_are_obsolete():
    current_doc = _doc_row(content="")
    old_chunk = _chunk_row("old-chunk", "previously searchable content")

    plan = plan_reconciliation(
        _result([current_doc]),
        existing_document_rows=[current_doc],
        existing_chunk_rows=[old_chunk],
    )

    assert plan.empty_document_ids == ("doc-1",)
    assert plan.obsolete_chunk_ids == ("old-chunk",)


def test_failed_url_is_neither_overwritten_nor_pruned():
    failed_doc = _doc_row("partial or stale content")
    failed_chunk = _chunk_row("failed-old-chunk", "persisted content")
    failure = IngestionFailure(URL, "OSError", "temporary fetch failure")

    plan = plan_reconciliation(
        _result([failed_doc], [_chunk_row("failed-new-chunk")], [failure]),
        existing_document_rows=[failed_doc],
        existing_chunk_rows=[failed_chunk],
    )

    assert plan.raw_document_upserts == ()
    assert plan.chunk_upserts == ()
    assert plan.obsolete_chunk_ids == ()
    assert plan.obsolete_chunk_urls == ()
    assert plan.failed_urls == (URL,)


def test_existing_chunk_with_mismatched_url_is_not_authorized_for_deletion():
    current_doc = _doc_row()
    mismatched_existing_chunk = _chunk_row(url="https://docs.python.org/different.html")

    with pytest.raises(ValueError, match="URL does not match"):
        plan_reconciliation(
            _result([current_doc]),
            existing_document_rows=[current_doc],
            existing_chunk_rows=[mismatched_existing_chunk],
        )


def test_identical_duplicate_ids_are_deduplicated_deterministically():
    document = _doc_row()
    chunk = _chunk_row()

    plan = plan_reconciliation(
        _result([document, document], [chunk, chunk]),
    )

    assert plan.raw_document_upserts == (document,)
    assert plan.chunk_upserts == (chunk,)


def test_conflicting_duplicate_ids_raise_instead_of_choosing_a_row():
    document = _doc_row()
    conflicting_document = {**document, "title": "Conflicting title"}
    chunk = _chunk_row()
    conflicting_chunk = {**chunk, "chunk_text": "different text"}

    with pytest.raises(ValueError, match="Conflicting raw document rows"):
        plan_reconciliation(_result([document, conflicting_document]))
    with pytest.raises(ValueError, match="Conflicting chunk rows"):
        plan_reconciliation(_result([document], [chunk, conflicting_chunk]))


def test_conflicting_duplicate_persisted_ids_are_rejected():
    document = _doc_row()
    chunk = _chunk_row()

    with pytest.raises(ValueError, match="Conflicting existing raw document"):
        plan_reconciliation(
            _result(),
            existing_document_rows=[document, {**document, "title": "Other title"}],
        )
    with pytest.raises(ValueError, match="Conflicting existing chunk"):
        plan_reconciliation(
            _result(),
            existing_chunk_rows=[chunk, {**chunk, "chunk_text": "Other text"}],
        )


def test_replanning_after_applying_plan_has_no_remaining_writes_or_deletes():
    old_doc = _doc_row("old document")
    old_chunk = _chunk_row("old-chunk", "old content")
    current_doc = _doc_row("updated document")
    current_chunk = _chunk_row("new-chunk", "new content")
    current_result = _result([current_doc], [current_chunk])

    first_plan = plan_reconciliation(
        current_result,
        existing_document_rows=[old_doc],
        existing_chunk_rows=[old_chunk],
    )
    persisted_docs = [current_doc]
    persisted_chunks = [current_chunk]
    retry_plan = plan_reconciliation(
        current_result,
        existing_document_rows=persisted_docs,
        existing_chunk_rows=persisted_chunks,
    )

    assert first_plan.obsolete_chunk_ids == ("old-chunk",)
    assert retry_plan.raw_document_upserts == ()
    assert retry_plan.chunk_upserts == ()
    assert retry_plan.obsolete_chunk_ids == ()
    assert retry_plan.empty_document_ids == ()
