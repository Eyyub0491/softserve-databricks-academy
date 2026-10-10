from types import SimpleNamespace

import pytest

from src.lab12_rag.databricks_retrieval import DatabricksVectorSearchRetriever


_COLUMNS = [
    "chunk_id", "doc_id", "source", "title", "url", "section",
    "chunk_index", "start_char", "end_char", "chunk_text",
]


def _row(chunk_id="chunk-1", section="Install", text="Install Python"):
    return [
        chunk_id, "doc-python", "Python docs", "Python Guide",
        "https://docs.python.org/guide", section, "2", "10", "24", text,
    ]


def _response(rows):
    return SimpleNamespace(
        manifest=SimpleNamespace(
            columns=[SimpleNamespace(name=name) for name in _COLUMNS]
        ),
        result=SimpleNamespace(data_array=rows),
    )


class FakeIndexClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def query_index(self, index_name, columns, **kwargs):
        self.calls.append((index_name, columns, kwargs))
        return self.response


def test_adapter_queries_managed_embedding_ann_and_maps_metadata_in_order():
    client = FakeIndexClient(_response([_row("first"), _row("second", section="Usage")]))
    retriever = DatabricksVectorSearchRetriever(client, "catalog.schema.python_chunks")

    chunks = retriever.search("install python", top_k=2)

    assert [chunk.chunk_id for chunk in chunks] == ["first", "second"]
    assert chunks[0].doc_id == "doc-python"
    assert chunks[0].source == "Python docs"
    assert chunks[0].title == "Python Guide"
    assert chunks[0].url == "https://docs.python.org/guide"
    assert chunks[0].section == "Install"
    assert (chunks[0].chunk_index, chunks[0].start_char, chunks[0].end_char) == (2, 10, 24)
    assert chunks[0].text == "Install Python"
    index_name, columns, kwargs = client.calls[0]
    assert index_name == "catalog.schema.python_chunks"
    assert columns == _COLUMNS
    assert kwargs["query_text"] == "install python"
    assert kwargs["query_columns"] == ["chunk_text"]
    assert kwargs["query_type"] == "ANN"
    assert kwargs["num_results"] == 2


def test_adapter_returns_empty_results():
    client = FakeIndexClient(_response([]))

    assert DatabricksVectorSearchRetriever(
        client, "catalog.schema.python_chunks"
    ).search("anything") == []


def test_adapter_passes_supported_string_equality_filters():
    client = FakeIndexClient(_response([_row()]))
    retriever = DatabricksVectorSearchRetriever(client, "catalog.schema.python_chunks")

    retriever.search("python", filters={"source": "Python docs", "section": "Install"})

    assert client.calls[0][2]["filters_json"] == '{"source": "Python docs", "section": "Install"}'


@pytest.mark.parametrize("filters", [{"chunk_text": "python"}, {"url": None}])
def test_adapter_rejects_unsupported_filters(filters):
    client = FakeIndexClient(_response([]))
    retriever = DatabricksVectorSearchRetriever(client, "catalog.schema.python_chunks")

    with pytest.raises(ValueError, match="Unsupported metadata filter|require string values"):
        retriever.search("python", filters=filters)

    assert client.calls == []


@pytest.mark.parametrize(
    "query, top_k, filters, message",
    [
        ("   ", 5, {"chunk_text": "python"}, "Unsupported metadata filter"),
        ("python", 0, {"source": None}, "require string values"),
    ],
)
def test_adapter_validates_filters_before_no_query_early_returns(
    query, top_k, filters, message
):
    client = FakeIndexClient(_response([]))
    retriever = DatabricksVectorSearchRetriever(client, "catalog.schema.python_chunks")

    with pytest.raises(ValueError, match=message):
        retriever.search(query, top_k=top_k, filters=filters)

    assert client.calls == []


def test_adapter_applies_zero_limit_without_querying_index():
    client = FakeIndexClient(_response([_row()]))
    retriever = DatabricksVectorSearchRetriever(client, "catalog.schema.python_chunks")

    assert retriever.search("python", top_k=0) == []
    assert client.calls == []


def test_adapter_rejects_malformed_response():
    client = FakeIndexClient(SimpleNamespace(manifest=None, result=None))

    with pytest.raises(ValueError, match="missing manifest columns"):
        DatabricksVectorSearchRetriever(
            client, "catalog.schema.python_chunks"
        ).search("python")
