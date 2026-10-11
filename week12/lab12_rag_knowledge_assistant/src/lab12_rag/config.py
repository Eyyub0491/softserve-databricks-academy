"""Local settings for document processing and future workspace integration."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping


DEFAULT_CHUNK_SIZE = 1_000
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_RETRIEVAL_TOP_K = 5
DEFAULT_CHAT_MAX_TOKENS = 512
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ENDPOINT_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class Lab12Config:
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    catalog: str | None = None
    schema: str | None = None
    vector_search_index_name: str | None = None
    retrieval_top_k: int = DEFAULT_RETRIEVAL_TOP_K
    chat_serving_endpoint_name: str | None = None
    chat_max_tokens: int = DEFAULT_CHAT_MAX_TOKENS

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("LAB12_CHUNK_SIZE must be greater than zero")
        if self.chunk_overlap < 0:
            raise ValueError("LAB12_CHUNK_OVERLAP must not be negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("LAB12_CHUNK_OVERLAP must be smaller than LAB12_CHUNK_SIZE")
        _validate_identifier("LAB12_CATALOG", self.catalog)
        _validate_identifier("LAB12_SCHEMA", self.schema)
        _validate_index_name(self.vector_search_index_name)
        _validate_endpoint_name(self.chat_serving_endpoint_name)
        if self.retrieval_top_k <= 0:
            raise ValueError("LAB12_RETRIEVAL_TOP_K must be greater than zero")
        if self.chat_max_tokens <= 0:
            raise ValueError("LAB12_CHAT_MAX_TOKENS must be greater than zero")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Lab12Config":
        """Load non-secret settings; no credential values are read or stored."""
        values = os.environ if env is None else env
        return cls(
            chunk_size=_read_int(values, "LAB12_CHUNK_SIZE", DEFAULT_CHUNK_SIZE),
            chunk_overlap=_read_int(
                values,
                "LAB12_CHUNK_OVERLAP",
                DEFAULT_CHUNK_OVERLAP,
            ),
            catalog=_optional_value(values, "LAB12_CATALOG"),
            schema=_optional_value(values, "LAB12_SCHEMA"),
            vector_search_index_name=_optional_value(values, "LAB12_VECTOR_SEARCH_INDEX_NAME"),
            retrieval_top_k=_read_int(
                values,
                "LAB12_RETRIEVAL_TOP_K",
                DEFAULT_RETRIEVAL_TOP_K,
            ),
            chat_serving_endpoint_name=_optional_value(
                values,
                "LAB12_CHAT_SERVING_ENDPOINT",
            ),
            chat_max_tokens=_read_int(
                values,
                "LAB12_CHAT_MAX_TOKENS",
                DEFAULT_CHAT_MAX_TOKENS,
            ),
        )

    def require_workspace_target(self) -> tuple[str, str]:
        """Return the configured catalog/schema or explain what is missing.

        Local parsing and chunking do not require a workspace target. Integration
        code can call this when a target has been explicitly configured.
        """
        missing = [
            name
            for name, value in (("LAB12_CATALOG", self.catalog), ("LAB12_SCHEMA", self.schema))
            if not value
        ]
        if missing:
            raise ValueError("Missing required workspace setting(s): " + ", ".join(missing))
        # __post_init__ validates both values when the config is constructed.
        assert self.catalog is not None and self.schema is not None
        return self.catalog, self.schema

    def require_query_targets(self) -> tuple[str, str]:
        """Return the configured AI Search index and chat serving endpoint."""
        missing = [
            name
            for name, value in (
                ("LAB12_VECTOR_SEARCH_INDEX_NAME", self.vector_search_index_name),
                ("LAB12_CHAT_SERVING_ENDPOINT", self.chat_serving_endpoint_name),
            )
            if not value
        ]
        if missing:
            raise ValueError("Missing required query setting(s): " + ", ".join(missing))
        assert self.vector_search_index_name is not None
        assert self.chat_serving_endpoint_name is not None
        return self.vector_search_index_name, self.chat_serving_endpoint_name


def _read_int(values: Mapping[str, str], name: str, default: int) -> int:
    raw = values.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None


def _optional_value(values: Mapping[str, str], name: str) -> str | None:
    value = values.get(name, "").strip()
    return value or None


def _validate_identifier(name: str, value: str | None) -> None:
    if value is not None and not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a simple SQL identifier")


def _validate_index_name(value: str | None) -> None:
    if value is None:
        return
    parts = value.split(".")
    if len(parts) != 3 or any(not _IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(
            "LAB12_VECTOR_SEARCH_INDEX_NAME must be a three-part SQL identifier "
            "(catalog.schema.index)"
        )


def _validate_endpoint_name(value: str | None) -> None:
    if value is not None and not _ENDPOINT_NAME.fullmatch(value):
        raise ValueError("LAB12_CHAT_SERVING_ENDPOINT must be a serving endpoint name")
