"""Prepare allowlisted documentation and chunks as local table rows."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from .chunking import chunk_document
from .config import Lab12Config
from .documents import ALLOWED_DOCUMENTS, DocumentRecord, fetch_document_html, parse_document
from .table_rows import chunk_to_row, document_to_raw_row


@dataclass(frozen=True, slots=True)
class IngestionFailure:
    url: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class PreparedIngestion:
    document_rows: tuple[dict[str, object], ...]
    chunk_rows: tuple[dict[str, object], ...]
    failures: tuple[IngestionFailure, ...]


FetchHTML = Callable[[str], str]
ParseDocument = Callable[[str, str], DocumentRecord]
Clock = Callable[[], datetime]


def prepare_ingestion(
    urls: Iterable[str] | None = None,
    *,
    config: Lab12Config | None = None,
    fetch_html: FetchHTML = fetch_document_html,
    parse: ParseDocument = parse_document,
    clock: Clock | None = None,
) -> PreparedIngestion:
    """Fetch, parse, chunk, and serialize each distinct input URL.

    Failures are retained per URL and do not prevent later URLs from being
    processed. This function prepares rows only; it does not write them.
    """
    source_urls = (
        (source.url for source in ALLOWED_DOCUMENTS)
        if urls is None
        else urls
    )
    settings = config or Lab12Config()
    timestamp = clock or _utc_now
    document_rows: list[dict[str, object]] = []
    chunk_rows: list[dict[str, object]] = []
    failures: list[IngestionFailure] = []
    seen_urls: set[str] = set()
    seen_doc_ids: set[str] = set()
    seen_chunk_ids: set[str] = set()

    for url in source_urls:
        if url in seen_urls:
            continue
        seen_urls.add(url)

        try:
            html_text = fetch_html(url)
            retrieved_at = timestamp()
            document = parse(url, html_text)
            chunks = chunk_document(
                document,
                chunk_size=settings.chunk_size,
                overlap=settings.chunk_overlap,
            )
            ingested_at = timestamp()
            chunked_at = timestamp()
            document_row = document_to_raw_row(
                document,
                retrieved_at=retrieved_at,
                ingested_at=ingested_at,
            )
            rows_for_document: list[dict[str, object]] = []
            document_chunk_ids: set[str] = set()
            for chunk in chunks:
                if chunk.chunk_id in seen_chunk_ids or chunk.chunk_id in document_chunk_ids:
                    continue
                rows_for_document.append(chunk_to_row(chunk, chunked_at=chunked_at))
                document_chunk_ids.add(chunk.chunk_id)
        except Exception as exc:
            failures.append(
                IngestionFailure(
                    url=url,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )
            continue

        if document.doc_id not in seen_doc_ids:
            document_rows.append(document_row)
            seen_doc_ids.add(document.doc_id)
        chunk_rows.extend(rows_for_document)
        seen_chunk_ids.update(row["chunk_id"] for row in rows_for_document)

    return PreparedIngestion(
        document_rows=tuple(document_rows),
        chunk_rows=tuple(chunk_rows),
        failures=tuple(failures),
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
