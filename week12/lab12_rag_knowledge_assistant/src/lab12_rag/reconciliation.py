"""Pure reconciliation planning for future Delta table writes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .ingestion import PreparedIngestion


_RAW_COMPARE_FIELDS = (
    "doc_id",
    "source",
    "title",
    "url",
    "content",
    "content_sha256",
)
_CHUNK_COMPARE_FIELDS = (
    "chunk_id",
    "doc_id",
    "source",
    "title",
    "url",
    "section",
    "chunk_index",
    "start_char",
    "end_char",
    "chunk_text",
    "chunk_sha256",
)


@dataclass(frozen=True, slots=True)
class ReconciliationPlan:
    """Deterministic row-level actions; no writes are performed by this plan."""

    raw_document_upserts: tuple[dict[str, object], ...]
    chunk_upserts: tuple[dict[str, object], ...]
    obsolete_chunk_ids: tuple[str, ...]
    empty_document_ids: tuple[str, ...]
    failed_urls: tuple[str, ...]
    obsolete_chunk_urls: tuple[tuple[str, str], ...] = ()


def plan_reconciliation(
    ingestion: PreparedIngestion,
    *,
    existing_document_rows: Iterable[Mapping[str, object] | str] = (),
    existing_chunk_rows: Iterable[Mapping[str, object]] = (),
) -> ReconciliationPlan:
    """Plan idempotent upserts and scoped stale-chunk deletions.

    Existing document IDs may be supplied as strings; full document rows allow
    unchanged payloads to be recognized. Existing chunks need ``chunk_id``,
    ``doc_id``, and ``url`` so deletion scope can be checked safely.
    """
    failed_urls = {failure.url for failure in ingestion.failures}
    existing_docs, existing_doc_urls = _existing_documents(existing_document_rows)
    existing_chunks = _existing_chunks(existing_chunk_rows)

    current_docs = _deduplicate_rows(
        (row for row in ingestion.document_rows if row.get("url") not in failed_urls),
        key_field="doc_id",
        row_name="raw document",
    )
    current_doc_urls = {doc_id: _required_url(row, "raw document") for doc_id, row in current_docs.items()}
    _validate_doc_urls(current_doc_urls, existing_doc_urls)

    current_chunks = _deduplicate_rows(
        (row for row in ingestion.chunk_rows if row.get("url") not in failed_urls),
        key_field="chunk_id",
        row_name="chunk",
    )
    for chunk_id, row in current_chunks.items():
        doc_id = _required_id(row, "doc_id", "chunk")
        if doc_id not in current_doc_urls:
            raise ValueError(f"Chunk {chunk_id!r} has no successfully processed document row")
        if row.get("url") != current_doc_urls[doc_id]:
            raise ValueError(f"Chunk {chunk_id!r} URL does not match its document row")

    raw_upserts = [
        row for doc_id, row in current_docs.items()
        if doc_id not in existing_docs
        or not _same_payload(row, existing_docs[doc_id], _RAW_COMPARE_FIELDS)
    ]
    chunk_upserts = [
        row for chunk_id, row in current_chunks.items()
        if chunk_id not in existing_chunks
        or not _same_payload(row, existing_chunks[chunk_id], _CHUNK_COMPARE_FIELDS)
    ]

    successful_doc_ids = set(current_docs)
    current_chunk_ids = set(current_chunks)
    obsolete_chunks: dict[str, str] = {}
    for chunk_id, row in existing_chunks.items():
        doc_id = _required_id(row, "doc_id", "existing chunk")
        url = _required_url(row, "existing chunk")
        if url in failed_urls:
            continue
        if doc_id in successful_doc_ids:
            if current_doc_urls[doc_id] != url:
                raise ValueError(
                    f"Existing chunk {chunk_id!r} URL does not match its document row"
                )
            if chunk_id not in current_chunk_ids:
                obsolete_chunks[chunk_id] = url

    docs_with_chunks = {row["doc_id"] for row in current_chunks.values()}
    empty_document_ids = successful_doc_ids - docs_with_chunks

    return ReconciliationPlan(
        raw_document_upserts=tuple(sorted(raw_upserts, key=lambda row: str(row["doc_id"]))),
        chunk_upserts=tuple(sorted(chunk_upserts, key=lambda row: str(row["chunk_id"]))),
        obsolete_chunk_ids=tuple(sorted(obsolete_chunks)),
        empty_document_ids=tuple(sorted(empty_document_ids)),
        failed_urls=tuple(sorted(failed_urls)),
        obsolete_chunk_urls=tuple(sorted(obsolete_chunks.items())),
    )


def _existing_documents(
    rows: Iterable[Mapping[str, object] | str],
) -> tuple[dict[str, Mapping[str, object]], dict[str, str]]:
    known: dict[str, Mapping[str, object]] = {}
    urls: dict[str, str] = {}
    for item in rows:
        if isinstance(item, str):
            doc_id = item
            row: Mapping[str, object] = {"doc_id": item}
        elif isinstance(item, Mapping):
            row = item
            doc_id = _required_id(row, "doc_id", "existing raw document")
        else:
            raise ValueError("Existing raw documents must be IDs or row mappings")
        _insert_unique(known, doc_id, row, "existing raw document")
        if "url" in row:
            url = _required_url(row, "existing raw document")
            previous_url = urls.setdefault(doc_id, url)
            if previous_url != url:
                raise ValueError(f"Conflicting URLs for existing document ID {doc_id!r}")
    return known, urls


def _existing_chunks(rows: Iterable[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    known: dict[str, Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("Existing chunks must be row mappings with chunk metadata")
        chunk_id = _required_id(row, "chunk_id", "existing chunk")
        _required_id(row, "doc_id", "existing chunk")
        _required_url(row, "existing chunk")
        _insert_unique(known, chunk_id, row, "existing chunk")
    return known


def _deduplicate_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    key_field: str,
    row_name: str,
) -> dict[str, Mapping[str, object]]:
    unique: dict[str, Mapping[str, object]] = {}
    for row in rows:
        key = _required_id(row, key_field, row_name)
        _insert_unique(unique, key, row, row_name)
    return unique


def _insert_unique(
    rows: dict[str, Mapping[str, object]],
    key: str,
    row: Mapping[str, object],
    row_name: str,
) -> None:
    previous = rows.get(key)
    if previous is not None and dict(previous) != dict(row):
        raise ValueError(f"Conflicting {row_name} rows for ID {key!r}")
    rows.setdefault(key, row)


def _required_id(row: Mapping[str, object], field: str, row_name: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{row_name} {field} must be a non-empty string")
    return value


def _required_url(row: Mapping[str, object], row_name: str) -> str:
    value = row.get("url")
    if not isinstance(value, str) or not value:
        raise ValueError(f"{row_name} URL must be a non-empty string")
    return value


def _validate_doc_urls(current: Mapping[str, str], existing: Mapping[str, str]) -> None:
    for doc_id, url in current.items():
        previous_url = existing.get(doc_id)
        if previous_url is not None and previous_url != url:
            raise ValueError(f"Document ID {doc_id!r} conflicts with its persisted URL")


def _same_payload(
    current: Mapping[str, object],
    existing: Mapping[str, object],
    fields: tuple[str, ...],
) -> bool:
    return all(field in current and field in existing and current[field] == existing[field] for field in fields)
