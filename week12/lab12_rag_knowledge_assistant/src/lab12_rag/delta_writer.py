"""Spark SQL persistence for Lab 12 reconciliation plans.

The Spark session and fully qualified table names are injected. This module
does not create a session or import Spark/Delta packages, so local tests can use
an offline fake. Each MERGE/DELETE is an independent Delta transaction; writes
across the two tables are not atomic together.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import re
from typing import Any
from uuid import uuid4

from .reconciliation import ReconciliationPlan


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RAW_FIELDS = (
    "doc_id", "source", "title", "url", "content", "content_sha256",
    "retrieved_at", "ingested_at",
)
_CHUNK_FIELDS = (
    "chunk_id", "doc_id", "source", "title", "url", "section",
    "chunk_index", "start_char", "end_char", "chunk_text", "chunk_sha256",
    "chunked_at",
)
_RAW_SCHEMA = (
    "doc_id STRING, source STRING, title STRING, url STRING, content STRING, "
    "content_sha256 STRING, retrieved_at TIMESTAMP, ingested_at TIMESTAMP"
)
_CHUNK_SCHEMA = (
    "chunk_id STRING, doc_id STRING, source STRING, title STRING, url STRING, "
    "section STRING, chunk_index INT, start_char INT, end_char INT, "
    "chunk_text STRING, chunk_sha256 STRING, chunked_at TIMESTAMP"
)
_DELETE_SCHEMA = "chunk_id STRING, url STRING"


@dataclass(frozen=True, slots=True)
class DeltaWriteResult:
    """Steps whose Delta statements completed successfully."""

    completed_steps: tuple[str, ...]


class DeltaPersistenceError(RuntimeError):
    """Write failure with completed steps so the same plan can be retried."""

    def __init__(self, failed_step: str, completed_steps: Sequence[str], cause: Exception):
        self.failed_step = failed_step
        self.completed_steps = tuple(completed_steps)
        super().__init__(
            f"Delta persistence failed during {failed_step}; completed steps: "
            f"{', '.join(self.completed_steps) or 'none'}: {cause}"
        )


class DeltaTableWriter:
    """Apply a reconciliation plan using injected Spark SQL operations."""

    def __init__(self, spark: Any, raw_documents_table: str, document_chunks_table: str):
        self._spark = spark
        self._raw_table = _validate_table_identifier(raw_documents_table)
        self._chunk_table = _validate_table_identifier(document_chunks_table)
        if self._raw_table == self._chunk_table:
            raise ValueError("Raw-document and chunk table names must be different")

    def persist(self, plan: ReconciliationPlan) -> DeltaWriteResult:
        raw_rows, chunk_rows, delete_rows = _validate_plan(plan)
        completed: list[str] = []
        steps = (
            ("raw_document_upserts", raw_rows, _RAW_SCHEMA, self._raw_table, "doc_id", self._raw_merge_sql),
            ("chunk_upserts", chunk_rows, _CHUNK_SCHEMA, self._chunk_table, "chunk_id", self._chunk_merge_sql),
            ("obsolete_chunk_deletions", delete_rows, _DELETE_SCHEMA, None, None, self._delete_sql),
        )
        for step_name, rows, schema, target_table, key_field, statement_builder in steps:
            if not rows:
                continue
            try:
                self._execute_rows(rows, schema, statement_builder, target_table, key_field)
            except Exception as exc:
                raise DeltaPersistenceError(step_name, completed, exc) from exc
            completed.append(step_name)
        return DeltaWriteResult(tuple(completed))

    def _execute_rows(self, rows, schema: str, statement_builder, target_table, key_field) -> None:
        view_name = f"lab12_write_{uuid4().hex}"
        frame = self._spark.createDataFrame(list(rows), schema=schema)
        frame.createOrReplaceTempView(view_name)
        try:
            if target_table is not None:
                duplicate_query = (
                    f"SELECT target.{key_field} FROM {target_table} AS target "
                    f"INNER JOIN {view_name} AS source "
                    f"ON target.{key_field} = source.{key_field} "
                    f"GROUP BY target.{key_field} HAVING COUNT(*) > 1 LIMIT 1"
                )
                if self._spark.sql(duplicate_query).take(1):
                    raise ValueError(
                        f"Target table {target_table} has duplicate {key_field} values "
                        "matching this upsert batch"
                    )
            self._spark.sql(statement_builder(view_name))
        finally:
            try:
                self._spark.catalog.dropTempView(view_name)
            except Exception:
                # A failed cleanup does not change whether the Delta statement committed.
                pass

    def _raw_merge_sql(self, source_view: str) -> str:
        changed = " OR ".join(
            f"NOT (target.{field} <=> source.{field})"
            for field in ("source", "title", "url", "content", "content_sha256")
        )
        assignments = ", ".join(
            f"{field} = source.{field}"
            for field in ("source", "title", "url", "content", "content_sha256", "retrieved_at")
        )
        assignments += ", ingested_at = current_timestamp()"
        columns = ", ".join(_RAW_FIELDS)
        values = ", ".join(
            "current_timestamp()" if field == "ingested_at" else f"source.{field}"
            for field in _RAW_FIELDS
        )
        return (
            f"MERGE INTO {self._raw_table} AS target USING {source_view} AS source "
            "ON target.doc_id = source.doc_id "
            f"WHEN MATCHED AND ({changed}) THEN UPDATE SET {assignments} "
            f"WHEN NOT MATCHED THEN INSERT ({columns}) VALUES ({values})"
        )

    def _chunk_merge_sql(self, source_view: str) -> str:
        changed = " OR ".join(
            f"NOT (target.{field} <=> source.{field})"
            for field in (
                "doc_id", "source", "title", "url", "section", "chunk_index",
                "start_char", "end_char", "chunk_text", "chunk_sha256",
            )
        )
        assignments = ", ".join(
            f"{field} = source.{field}"
            for field in (
                "doc_id", "source", "title", "url", "section", "chunk_index",
                "start_char", "end_char", "chunk_text", "chunk_sha256", "chunked_at",
            )
        )
        columns = ", ".join(_CHUNK_FIELDS)
        values = ", ".join(f"source.{field}" for field in _CHUNK_FIELDS)
        return (
            f"MERGE INTO {self._chunk_table} AS target USING {source_view} AS source "
            "ON target.chunk_id = source.chunk_id "
            f"WHEN MATCHED AND ({changed}) THEN UPDATE SET {assignments} "
            f"WHEN NOT MATCHED THEN INSERT ({columns}) VALUES ({values})"
        )

    def _delete_sql(self, source_view: str) -> str:
        return (
            f"DELETE FROM {self._chunk_table} AS target WHERE EXISTS ("
            f"SELECT 1 FROM {source_view} AS obsolete "
            "WHERE target.chunk_id = obsolete.chunk_id AND target.url = obsolete.url)"
        )


def _validate_table_identifier(value: str) -> str:
    parts = value.split(".") if isinstance(value, str) else []
    if len(parts) != 3 or any(not _IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError("Table name must be a fully qualified catalog.schema.table identifier")
    return value


def _validate_plan(plan: ReconciliationPlan):
    if not isinstance(plan, ReconciliationPlan):
        raise TypeError("plan must be a ReconciliationPlan")
    failed_urls = set(plan.failed_urls)
    raw_rows = _validate_rows(plan.raw_document_upserts, _RAW_FIELDS, "raw document")
    chunk_rows = _validate_rows(plan.chunk_upserts, _CHUNK_FIELDS, "chunk")

    for row in raw_rows:
        if row["url"] in failed_urls:
            raise ValueError("Plan contains a raw-document upsert for a failed URL")
    for row in chunk_rows:
        if row["url"] in failed_urls:
            raise ValueError("Plan contains a chunk upsert for a failed URL")

    deletion_ids = tuple(plan.obsolete_chunk_ids)
    deletion_pairs = tuple(plan.obsolete_chunk_urls)
    if len(set(deletion_ids)) != len(deletion_ids):
        raise ValueError("Plan contains duplicate obsolete chunk IDs")
    if {chunk_id for chunk_id, _ in deletion_pairs} != set(deletion_ids):
        raise ValueError("Plan obsolete chunk URL metadata must match obsolete chunk IDs")
    if len(deletion_pairs) != len(deletion_ids):
        raise ValueError("Plan contains duplicate obsolete chunk URL metadata")
    delete_rows: list[dict[str, object]] = []
    for chunk_id, url in deletion_pairs:
        if not isinstance(chunk_id, str) or not chunk_id or not isinstance(url, str) or not url:
            raise ValueError("Obsolete chunk deletion requires non-empty chunk IDs and URLs")
        if url in failed_urls:
            raise ValueError("Plan contains an obsolete chunk deletion for a failed URL")
        delete_rows.append({"chunk_id": chunk_id, "url": url})
    return raw_rows, chunk_rows, delete_rows


def _validate_rows(rows, fields: tuple[str, ...], row_name: str) -> list[dict[str, object]]:
    validated: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    key = "doc_id" if row_name == "raw document" else "chunk_id"
    string_fields = (
        ("doc_id", "source", "title", "url", "content", "content_sha256")
        if row_name == "raw document"
        else ("chunk_id", "doc_id", "source", "title", "url", "chunk_text", "chunk_sha256")
    )
    nullable_fields = {"retrieved_at"} if row_name == "raw document" else {"section"}
    timestamp_fields = {"retrieved_at", "ingested_at"} if row_name == "raw document" else {"chunked_at"}
    integer_fields = set() if row_name == "raw document" else {"chunk_index", "start_char", "end_char"}

    for row in rows:
        if not isinstance(row, Mapping) or set(row) != set(fields):
            raise ValueError(f"{row_name} row fields do not match the Delta table schema")
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{row_name} {key} must be a non-empty string")
        if value in seen_ids:
            raise ValueError(f"Plan contains duplicate {row_name} ID {value!r}")
        seen_ids.add(value)

        for field in string_fields:
            if not isinstance(row[field], str):
                raise ValueError(f"{row_name} field {field} must be a string")
        text_field, hash_field = (
            ("content", "content_sha256")
            if row_name == "raw document"
            else ("chunk_text", "chunk_sha256")
        )
        expected_hash = sha256(row[text_field].encode("utf-8")).hexdigest()
        if row[hash_field] != expected_hash:
            raise ValueError(f"{row_name} field {hash_field} does not match its text")
        for field in nullable_fields:
            if row[field] is not None and not isinstance(row[field], str if field == "section" else datetime):
                raise ValueError(f"{row_name} field {field} has an invalid nullable type")
        for field in timestamp_fields - nullable_fields:
            if not isinstance(row[field], datetime):
                raise ValueError(f"{row_name} field {field} must be a datetime")
        for field in integer_fields:
            if not isinstance(row[field], int) or isinstance(row[field], bool):
                raise ValueError(f"{row_name} field {field} must be an integer")
        validated.append(dict(row))
    return validated
