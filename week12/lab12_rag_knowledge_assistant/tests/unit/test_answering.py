from src.lab12_rag.answering import (
    NO_CONTEXT_ANSWER,
    answer_with_retrieval,
    answer_without_retrieval,
)
from src.lab12_rag.chunking import DocumentChunk
from src.lab12_rag.retrieval import InMemoryRetriever


def _chunk(chunk_id: str, text: str, *, url: str, section: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        doc_id="python-json",
        source="Python documentation",
        title="json — JSON encoder and decoder",
        url=url,
        section=section,
        chunk_index=0,
        start_char=0,
        end_char=len(text),
        text=text,
    )


class FakeGenerator:
    def __init__(self):
        self.calls = []

    def generate(self, query, context):
        self.calls.append((query, tuple(context)))
        return "fake answer with context" if context else "fake baseline answer"


def test_rag_passes_context_and_returns_source_references_and_chunk_ids():
    chunks = [
        _chunk(
            "chunk-1",
            "JSON encodes structured data",
            url="https://docs.python.org/3/library/json.html",
            section="Encoding",
        ),
        _chunk(
            "chunk-2",
            "JSON decoder parses structured data",
            url="https://docs.python.org/3/library/json.html",
            section="Decoding",
        ),
    ]
    generator = FakeGenerator()

    result = answer_with_retrieval(
        "JSON structured data",
        InMemoryRetriever(chunks),
        generator,
        top_k=2,
    )

    assert result.answer == "fake answer with context"
    assert result.mode == "rag"
    assert result.context_available is True
    assert result.retrieved_chunk_ids == ("chunk-1", "chunk-2")
    assert [reference.url for reference in result.source_references] == [
        "https://docs.python.org/3/library/json.html",
        "https://docs.python.org/3/library/json.html",
    ]
    assert [reference.section for reference in result.source_references] == ["Encoding", "Decoding"]
    assert generator.calls == [("JSON structured data", tuple(chunks))]


def test_empty_retrieval_abstains_without_calling_generator_or_fabricating_sources():
    generator = FakeGenerator()

    result = answer_with_retrieval(
        "unmatched question",
        InMemoryRetriever([_chunk(
            "chunk-1",
            "Python JSON encoder",
            url="https://docs.python.org/3/library/json.html",
            section="Encoding",
        )]),
        generator,
    )

    assert result.answer == NO_CONTEXT_ANSWER
    assert result.mode == "rag"
    assert result.context_available is False
    assert result.source_references == ()
    assert result.retrieved_chunk_ids == ()
    assert generator.calls == []


def test_no_retrieval_baseline_uses_same_generator_without_context():
    generator = FakeGenerator()

    result = answer_without_retrieval("What does JSON do?", generator)

    assert result.answer == "fake baseline answer"
    assert result.mode == "baseline"
    assert result.context_available is False
    assert result.source_references == ()
    assert result.retrieved_chunk_ids == ()
    assert generator.calls == [("What does JSON do?", ())]
