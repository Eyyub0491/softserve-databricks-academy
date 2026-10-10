import pytest

from src.lab12_rag.chunking import DocumentChunk
from src.lab12_rag.retrieval import InMemoryRetriever


def _chunk(chunk_id: str, text: str, *, source: str = "Python docs", url: str | None = None):
    return DocumentChunk(
        chunk_id=chunk_id,
        doc_id=f"doc-{chunk_id}",
        source=source,
        title=f"Title {chunk_id}",
        url=url or f"https://docs.python.org/{chunk_id}",
        section="Examples",
        chunk_index=0,
        start_char=0,
        end_char=len(text),
        text=text,
    )


def test_retrieval_orders_by_lexical_overlap_and_applies_top_k():
    chunks = [
        _chunk("one", "Python JSON encoder"),
        _chunk("two", "JSON JSON decoder"),
        _chunk("three", "Python pathlib files"),
    ]

    results = InMemoryRetriever(chunks).search("json decoder", top_k=2)

    assert [chunk.chunk_id for chunk in results] == ["two", "one"]


def test_retrieval_filters_metadata_before_ranking():
    chunks = [
        _chunk("one", "Python JSON encoder", source="Python tutorial"),
        _chunk("two", "Python JSON decoder", source="Python library"),
    ]

    results = InMemoryRetriever(chunks).search(
        "python json", filters={"source": "Python library"}
    )

    assert [chunk.chunk_id for chunk in results] == ["two"]


def test_retrieval_returns_no_results_for_blank_or_unmatched_query():
    retriever = InMemoryRetriever([_chunk("one", "Python JSON encoder")])

    assert retriever.search("   ") == []
    assert retriever.search("volcano") == []


def test_retrieval_validates_top_k_and_metadata_filters():
    retriever = InMemoryRetriever([_chunk("one", "Python")])

    with pytest.raises(ValueError, match="top_k"):
        retriever.search("python", top_k=-1)
    with pytest.raises(ValueError, match="Unsupported metadata filter"):
        retriever.search("python", filters={"chunk_text": "Python"})
