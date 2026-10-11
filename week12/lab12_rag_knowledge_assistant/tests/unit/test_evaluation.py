import pytest

from src.lab12_rag.chunking import DocumentChunk
from src.lab12_rag.evaluation import EvaluationCase, compare_rag_with_baseline


class FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def search(self, query, top_k=5, filters=None):
        self.calls.append((query, top_k, filters))
        return self.chunks[:top_k]


class FakeGenerator:
    def __init__(self):
        self.calls = []

    def generate(self, query, context):
        self.calls.append((query, tuple(context)))
        return "RAG answer" if context else "Baseline answer"


def _chunk():
    return DocumentChunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        source="Python documentation",
        title="Python JSON",
        url="https://docs.python.org/3/library/json.html",
        section="Encoding",
        chunk_index=0,
        start_char=0,
        end_char=14,
        text="JSON encodes data",
    )


def test_comparison_runs_fixed_cases_in_order_for_rag_and_baseline():
    cases = (
        EvaluationCase("json-1", "What is JSON for?"),
        EvaluationCase("json-2", "How is JSON encoded?"),
    )
    retriever = FakeRetriever([_chunk()])
    generator = FakeGenerator()

    comparisons = compare_rag_with_baseline(
        cases,
        retriever,
        generator,
        top_k=3,
    )

    assert [item.case.case_id for item in comparisons] == ["json-1", "json-2"]
    assert [(item.rag.answer, item.baseline.answer) for item in comparisons] == [
        ("RAG answer", "Baseline answer"),
        ("RAG answer", "Baseline answer"),
    ]
    assert all(item.rag.mode == "rag" and item.baseline.mode == "baseline" for item in comparisons)
    assert retriever.calls == [
        ("What is JSON for?", 3, None),
        ("How is JSON encoded?", 3, None),
    ]
    assert [context for _, context in generator.calls] == [
        (_chunk(),),
        (),
        (_chunk(),),
        (),
    ]


def test_comparison_rejects_duplicate_or_blank_cases():
    retriever = FakeRetriever([_chunk()])
    generator = FakeGenerator()

    with pytest.raises(ValueError, match="Duplicate evaluation case ID"):
        compare_rag_with_baseline(
            (EvaluationCase("same", "one"), EvaluationCase("same", "two")),
            retriever,
            generator,
        )

    with pytest.raises(ValueError, match="must not be empty"):
        compare_rag_with_baseline((EvaluationCase("blank", "  "),), retriever, generator)
