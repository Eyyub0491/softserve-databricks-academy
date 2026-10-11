from datetime import datetime, timedelta, timezone

from src.lab12_rag.config import Lab12Config
from src.lab12_rag.documents import ALLOWED_DOCUMENTS
from src.lab12_rag.ingestion import prepare_ingestion


_HTML = "<html><head><title>Test page</title></head><body><h1>Examples</h1><p>offline ingestion content</p></body></html>"


def _clock():
    start = datetime(2026, 2, 1, tzinfo=timezone.utc)
    calls = []

    def now():
        value = start + timedelta(seconds=len(calls))
        calls.append(value)
        return value

    return now, calls


def test_prepare_ingestion_processes_allowlisted_urls_and_maps_rows():
    urls = [source.url for source in ALLOWED_DOCUMENTS[:2]]
    fetched = []
    clock, clock_calls = _clock()

    result = prepare_ingestion(
        urls,
        fetch_html=lambda url: fetched.append(url) or _HTML,
        config=Lab12Config(chunk_size=100, chunk_overlap=10),
        clock=clock,
    )

    assert fetched == urls
    assert len(result.document_rows) == 2
    assert len(result.chunk_rows) == 2
    assert result.failures == ()
    assert [row["url"] for row in result.document_rows] == urls
    assert [row["doc_id"] for row in result.document_rows] == [
        row["doc_id"] for row in result.chunk_rows
    ]
    assert all(row["chunk_text"] == "offline ingestion content" for row in result.chunk_rows)
    assert result.document_rows[0]["retrieved_at"] == clock_calls[0]
    assert result.document_rows[0]["ingested_at"] == clock_calls[1]
    assert result.chunk_rows[0]["chunked_at"] == clock_calls[2]


def test_prepare_ingestion_continues_after_individual_url_failure():
    urls = [source.url for source in ALLOWED_DOCUMENTS[:2]]

    def fetch(url):
        if url == urls[0]:
            raise OSError("offline fixture failure")
        return _HTML

    clock, _ = _clock()
    result = prepare_ingestion(urls, fetch_html=fetch, clock=clock)

    assert len(result.document_rows) == 1
    assert len(result.chunk_rows) == 1
    assert len(result.failures) == 1
    assert result.failures[0].url == urls[0]
    assert result.failures[0].error_type == "OSError"
    assert result.failures[0].message == "offline fixture failure"
    assert result.document_rows[0]["url"] == urls[1]


def test_prepare_ingestion_empty_input_does_no_work():
    def unexpected_call(*_args):
        raise AssertionError("empty input must not fetch, parse, or read the clock")

    result = prepare_ingestion([], fetch_html=unexpected_call, parse=unexpected_call, clock=unexpected_call)

    assert result.document_rows == ()
    assert result.chunk_rows == ()
    assert result.failures == ()


def test_prepare_ingestion_deduplicates_repeated_input_urls():
    url = ALLOWED_DOCUMENTS[0].url
    fetched = []
    clock, _ = _clock()

    result = prepare_ingestion(
        [url, url, url],
        fetch_html=lambda requested_url: fetched.append(requested_url) or _HTML,
        clock=clock,
    )

    assert fetched == [url]
    assert len(result.document_rows) == 1
    assert len(result.chunk_rows) == 1
    assert result.failures == ()


def test_prepare_ingestion_defaults_to_all_allowlisted_urls():
    fetched = []
    clock, _ = _clock()

    result = prepare_ingestion(
        fetch_html=lambda url: fetched.append(url) or _HTML,
        clock=clock,
    )

    assert fetched == [source.url for source in ALLOWED_DOCUMENTS]
    assert len(result.document_rows) == len(ALLOWED_DOCUMENTS)
    assert len(result.chunk_rows) == len(ALLOWED_DOCUMENTS)
    assert result.failures == ()
