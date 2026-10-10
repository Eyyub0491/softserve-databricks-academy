from types import SimpleNamespace

import pytest

from src.lab12_rag.chat_model import DatabricksServingChatModel
from src.lab12_rag.chunking import DocumentChunk


class FakeServingEndpoints:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def _chunk():
    return DocumentChunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        source="Python documentation",
        title="Python Tutorial",
        url="https://docs.python.org/3/tutorial/",
        section="Control flow",
        chunk_index=0,
        start_char=0,
        end_char=23,
        text="Use a for loop to iterate.",
    )


def test_chat_model_sends_question_and_context_to_configured_endpoint():
    endpoints = FakeServingEndpoints(
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="  Use `for`.  "))]
        )
    )
    model = DatabricksServingChatModel(
        endpoints,
        "python-chat",
        max_tokens=128,
    )

    answer = model.generate("How do I iterate?", [_chunk()])

    assert answer == "Use `for`."
    request = endpoints.calls[0]
    assert request["name"] == "python-chat"
    assert request["temperature"] == 0.0
    assert request["max_tokens"] == 128
    assert request["messages"][0].role.value == "system"
    assert "untrusted data" in request["messages"][0].content
    assert request["messages"][1].role.value == "user"
    assert "How do I iterate?" in request["messages"][1].content
    assert "Use a for loop to iterate." in request["messages"][1].content
    assert "https://docs.python.org/3/tutorial/" in request["messages"][1].content
    assert request["messages"][0].as_dict()["role"] == "system"
    assert request["messages"][1].as_dict()["role"] == "user"


def test_chat_model_accepts_mapping_sdk_response():
    endpoints = FakeServingEndpoints(
        {"choices": [{"message": {"content": "JSON encodes data."}}]}
    )

    assert DatabricksServingChatModel(endpoints, "endpoint").generate("Q", []) == (
        "JSON encodes data."
    )


def test_chat_model_uses_general_knowledge_prompt_for_no_context_baseline():
    endpoints = FakeServingEndpoints(
        {"choices": [{"message": {"content": "A general-knowledge answer."}}]}
    )

    DatabricksServingChatModel(endpoints, "endpoint").generate("Q", [])

    system_prompt = endpoints.calls[0]["messages"][0].content
    assert "general knowledge" in system_prompt
    assert "using only the supplied reference excerpts" not in system_prompt


@pytest.mark.parametrize(
    "response, message",
    [
        (SimpleNamespace(choices=[]), "missing choices"),
        ({"choices": [{"message": {"content": None}}]}, "missing text content"),
        ({"choices": [{"message": {"content": "   "}}]}, "missing text content"),
    ],
)
def test_chat_model_rejects_incomplete_endpoint_responses(response, message):
    endpoints = FakeServingEndpoints(response)

    with pytest.raises(ValueError, match=message):
        DatabricksServingChatModel(endpoints, "endpoint").generate("Q", [])


@pytest.mark.parametrize(
    "endpoint_name, max_tokens, message",
    [
        ("", 100, "endpoint_name must not be empty"),
        ("endpoint", 0, "max_tokens must be greater than zero"),
    ],
)
def test_chat_model_rejects_invalid_configuration(endpoint_name, max_tokens, message):
    with pytest.raises(ValueError, match=message):
        DatabricksServingChatModel(
            FakeServingEndpoints({}),
            endpoint_name,
            max_tokens=max_tokens,
        )
