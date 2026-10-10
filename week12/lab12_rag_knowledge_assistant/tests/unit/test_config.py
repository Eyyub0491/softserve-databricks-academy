import pytest

from src.lab12_rag.config import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    Lab12Config,
)


def test_config_loads_local_defaults_without_credentials():
    config = Lab12Config.from_env({})

    assert config.chunk_size == DEFAULT_CHUNK_SIZE
    assert config.chunk_overlap == DEFAULT_CHUNK_OVERLAP
    assert config.catalog is None
    assert config.schema is None
    assert config.vector_search_index_name is None
    assert config.retrieval_top_k == 5
    assert config.chat_serving_endpoint_name is None
    assert config.chat_max_tokens == 512
    assert not hasattr(config, "token")
    assert not hasattr(config, "password")


def test_config_reads_nonsecret_environment_settings():
    config = Lab12Config.from_env(
        {
            "LAB12_CHUNK_SIZE": "400",
            "LAB12_CHUNK_OVERLAP": "50",
            "LAB12_CATALOG": "training_data",
            "LAB12_SCHEMA": "lab12_rag",
            "LAB12_VECTOR_SEARCH_INDEX_NAME": "training_data.lab12_rag.document_chunks",
            "LAB12_RETRIEVAL_TOP_K": "8",
            "LAB12_CHAT_SERVING_ENDPOINT": "python-chat-endpoint",
            "LAB12_CHAT_MAX_TOKENS": "768",
        }
    )

    assert (config.chunk_size, config.chunk_overlap) == (400, 50)
    assert config.vector_search_index_name == "training_data.lab12_rag.document_chunks"
    assert config.retrieval_top_k == 8
    assert config.chat_serving_endpoint_name == "python-chat-endpoint"
    assert config.chat_max_tokens == 768
    assert config.require_workspace_target() == ("training_data", "lab12_rag")
    assert config.require_query_targets() == (
        "training_data.lab12_rag.document_chunks",
        "python-chat-endpoint",
    )


@pytest.mark.parametrize(
    "env, message",
    [
        ({"LAB12_CHUNK_SIZE": "abc"}, "must be an integer"),
        ({"LAB12_CHUNK_SIZE": "0"}, "greater than zero"),
        ({"LAB12_CHUNK_SIZE": "10", "LAB12_CHUNK_OVERLAP": "10"}, "smaller than"),
        ({"LAB12_CHUNK_OVERLAP": "-1"}, "must not be negative"),
        ({"LAB12_CATALOG": "bad.catalog"}, "simple SQL identifier"),
        ({"LAB12_VECTOR_SEARCH_INDEX_NAME": "bad"}, "three-part SQL identifier"),
        ({"LAB12_RETRIEVAL_TOP_K": "0"}, "greater than zero"),
        ({"LAB12_CHAT_MAX_TOKENS": "0"}, "greater than zero"),
        ({"LAB12_CHAT_SERVING_ENDPOINT": "bad.endpoint"}, "serving endpoint name"),
    ],
)
def test_config_rejects_invalid_settings(env, message):
    with pytest.raises(ValueError, match=message):
        Lab12Config.from_env(env)


def test_workspace_target_reports_missing_required_values():
    with pytest.raises(ValueError, match="LAB12_CATALOG, LAB12_SCHEMA"):
        Lab12Config.from_env({}).require_workspace_target()


def test_workspace_target_reports_one_missing_value():
    with pytest.raises(ValueError, match="LAB12_SCHEMA"):
        Lab12Config.from_env({"LAB12_CATALOG": "training_data"}).require_workspace_target()


def test_query_targets_report_missing_nonsecret_settings():
    with pytest.raises(
        ValueError,
        match="LAB12_VECTOR_SEARCH_INDEX_NAME, LAB12_CHAT_SERVING_ENDPOINT",
    ):
        Lab12Config.from_env({}).require_query_targets()
