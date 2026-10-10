from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import re

import pytest

from src.lab12_rag.delta_writer import (
    DeltaPersistenceError,
    DeltaTableWriter,
)
from src.lab12_rag.ingestion import IngestionFailure, PreparedIngestion
from src.lab12_rag.reconciliation import plan_reconciliation


URL = "https://docs.python.org/3/library/json.html"
STAMP = datetime(2026, 4, 1, tzinfo=timezone.utc)
COMMIT_TIME = datetime(2026, 4, 2, tzinfo=timezone.utc)
RAW_TABLE = "lab12.default.raw_documents"
CHUNK_TABLE = "lab12.default.document_chunks"


def _hash(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _doc(text="document", *, ingested_at=STAMP):
    return {
        "doc_id": "doc-1",
        "source": "Python documentation",
        "title": "JSON",
        "url": URL,
        "content": text,
        "content_sha256": _hash(text),
        "retrieved_at": STAMP,
        "ingested_at": ingested_at,
    }


def _chunk(chunk_id="chunk-1", text="chunk", *, chunked_at=STAMP):
    return {
        "chunk_id": chunk_id,
        "doc_id": "doc-1",
        "source": "Python documentation",
        "title": "JSON",
        "url": URL,
        "section": "Examples",
        "chunk_index": 0,
        "start_char": 0,
        "end_char": len(text),
        "chunk_text": text,
        "chunk_sha256": _hash(text),
        "chunked_at": chunked_at,
    }


def _plan(documents=(), chunks=(), *, failures=(), existing_docs=(), existing_chunks=()):
    ingestion = PreparedIngestion(tuple(documents), tuple(chunks), tuple(failures))
    return plan_reconciliation(
        ingestion,
        existing_document_rows=existing_docs,
        existing_chunk_rows=existing_chunks,
    )


class FakeFrame:
    def __init__(self, spark, rows, schema):
        self.spark = spark
        self.rows = [dict(row) for row in rows]
        self.schema = schema

    def createOrReplaceTempView(self, name):
        self.spark.views[name] = self.rows
        self.spark.created_schemas.append(self.schema)


class FakeCatalog:
    def __init__(self, spark):
        self.spark = spark

    def dropTempView(self, name):
        self.spark.views.pop(name, None)
        return True


class FakeQueryResult:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def take(self, count):
        return self.rows[:count]


class FakeSpark:
    """Offline SQL fake for the writer's fixed MERGE and DELETE statements."""

    def __init__(self, *, fail_on_call=None):
        self.tables = {RAW_TABLE: [], CHUNK_TABLE: []}
        self.views = {}
        self.created_schemas = []
        self.statements = []
        self.fail_on_call = fail_on_call
        self.catalog = FakeCatalog(self)

    def createDataFrame(self, rows, schema):
        return FakeFrame(self, rows, schema)

    def sql(self, statement):
        self.statements.append(statement)
        if self.fail_on_call == len(self.statements):
            raise RuntimeError("simulated statement failure")
        duplicate = re.match(
            r"SELECT target\.(doc_id|chunk_id) FROM ([\w.]+) AS target "
            r"INNER JOIN (\w+) AS source ON target\.\1 = source\.\1 "
            r"GROUP BY target\.\1 HAVING COUNT\(\*\) > 1 LIMIT 1",
            statement,
        )
        if duplicate:
            key, table, view = duplicate.groups()
            batch_keys = {row[key] for row in self.views[view]}
            counts = {}
            for row in self.tables[table]:
                if row[key] in batch_keys:
                    counts[row[key]] = counts.get(row[key], 0) + 1
            return FakeQueryResult(key for key, count in counts.items() if count > 1)
        merge = re.match(r"MERGE INTO ([\w.]+) AS target USING (\w+) AS source", statement)
        if merge:
            table, view = merge.groups()
            source_rows = self.views[view]
            key = "doc_id" if table == RAW_TABLE else "chunk_id"
            self._merge_rows(table, source_rows, key)
            return None
        delete = re.match(r"DELETE FROM ([\w.]+) AS target WHERE EXISTS \(SELECT 1 FROM (\w+) AS obsolete", statement)
        if delete:
            table, view = delete.groups()
            pairs = {(row["chunk_id"], row["url"]) for row in self.views[view]}
            self.tables[table] = [
                row for row in self.tables[table]
                if (row["chunk_id"], row["url"]) not in pairs
            ]
            return None
        raise AssertionError(f"Unexpected SQL statement: {statement}")

    def _merge_rows(self, table, source_rows, key):
        target_rows = self.tables[table]
        comparison_fields = (
            ("source", "title", "url", "content", "content_sha256")
            if key == "doc_id"
            else (
                "doc_id", "source", "title", "url", "section", "chunk_index",
                "start_char", "end_char", "chunk_text", "chunk_sha256",
            )
        )
        for source in source_rows:
            match = next((row for row in target_rows if row[key] == source[key]), None)
            if match is None:
                inserted = dict(source)
                if key == "doc_id":
                    inserted["ingested_at"] = COMMIT_TIME
                target_rows.append(inserted)
            elif any(match[field] != source[field] for field in comparison_fields):
                match.update(source)
                if key == "doc_id":
                    match["ingested_at"] = COMMIT_TIME


def _writer(spark):
    return DeltaTableWriter(spark, RAW_TABLE, CHUNK_TABLE)


def test_writer_merges_raw_and_chunk_rows_and_sets_persisted_timestamp():
    spark = FakeSpark()
    plan = _plan([_doc()], [_chunk()])

    result = _writer(spark).persist(plan)

    assert result.completed_steps == ("raw_document_upserts", "chunk_upserts")
    assert len(spark.tables[RAW_TABLE]) == len(spark.tables[CHUNK_TABLE]) == 1
    assert spark.tables[RAW_TABLE][0]["ingested_at"] == COMMIT_TIME
    assert spark.tables[RAW_TABLE][0]["ingested_at"] != plan.raw_document_upserts[0]["ingested_at"]
    assert "current_timestamp()" in spark.statements[1]
    assert not spark.views


def test_writer_handles_empty_plan_without_dataframe_or_sql_operations():
    spark = FakeSpark()

    result = _writer(spark).persist(_plan())

    assert result.completed_steps == ()
    assert spark.statements == []
    assert spark.created_schemas == []


def test_writer_deletes_stale_chunks_and_empty_document_chunks():
    spark = FakeSpark()
    old = _chunk("old", "stale")
    spark.tables[CHUNK_TABLE] = [old]
    plan = _plan(
        [_doc("")],
        existing_docs=[_doc("")],
        existing_chunks=[old],
    )

    result = _writer(spark).persist(plan)

    assert plan.empty_document_ids == ("doc-1",)
    assert result.completed_steps == ("obsolete_chunk_deletions",)
    assert spark.tables[CHUNK_TABLE] == []


def test_failed_url_rows_are_not_written_or_deleted():
    spark = FakeSpark()
    stale = _chunk()
    spark.tables[CHUNK_TABLE] = [stale]
    failure = IngestionFailure(URL, "OSError", "fetch failed")
    plan = _plan([_doc()], [_chunk("new")], failures=[failure], existing_chunks=[stale])

    result = _writer(spark).persist(plan)

    assert result.completed_steps == ()
    assert spark.tables[CHUNK_TABLE] == [stale]
    assert spark.tables[RAW_TABLE] == []
    assert spark.statements == []


def test_writer_rejects_plan_that_authorizes_deletion_for_failed_url():
    spark = FakeSpark()
    plan = _plan(failures=[IngestionFailure(URL, "OSError", "fetch failed")])
    unsafe_plan = replace(
        plan,
        obsolete_chunk_ids=("old",),
        obsolete_chunk_urls=(("old", URL),),
    )

    with pytest.raises(ValueError, match="deletion for a failed URL"):
        _writer(spark).persist(unsafe_plan)
    assert spark.statements == []


def test_writer_validates_fully_qualified_tables_and_row_shapes():
    spark = FakeSpark()
    with pytest.raises(ValueError, match="fully qualified"):
        DeltaTableWriter(spark, "lab12.default.raw-documents", CHUNK_TABLE)

    plan = _plan([_doc()], [_chunk()])
    malformed = replace(plan, raw_document_upserts=({"doc_id": "doc-1"},))
    with pytest.raises(ValueError, match="row fields do not match"):
        _writer(spark).persist(malformed)
    assert spark.statements == []


def test_writer_rejects_text_hash_mismatch_before_writing():
    spark = FakeSpark()
    document = {**_doc(), "content_sha256": _hash("different content")}
    with pytest.raises(ValueError, match="does not match its text"):
        _writer(spark).persist(_plan([document]))
    assert spark.statements == []


def test_repeating_same_plan_is_idempotent_in_fake_delta_state():
    spark = FakeSpark()
    plan = _plan([_doc()], [_chunk()])
    writer = _writer(spark)

    writer.persist(plan)
    first_raw = dict(spark.tables[RAW_TABLE][0])
    writer.persist(plan)

    assert len(spark.tables[RAW_TABLE]) == 1
    assert len(spark.tables[CHUNK_TABLE]) == 1
    assert spark.tables[RAW_TABLE][0] == first_raw
    assert spark.tables[RAW_TABLE][0]["ingested_at"] == COMMIT_TIME


def test_partial_failure_reports_completed_step_and_same_plan_retries_safely():
    old = _chunk("old", "old content")
    spark = FakeSpark(fail_on_call=4)
    spark.tables[CHUNK_TABLE] = [old]
    plan = _plan(
        [_doc("new document")],
        [_chunk("new", "new content")],
        existing_docs=[_doc("old document")],
        existing_chunks=[old],
    )
    writer = _writer(spark)

    with pytest.raises(DeltaPersistenceError) as error:
        writer.persist(plan)
    assert error.value.failed_step == "chunk_upserts"
    assert error.value.completed_steps == ("raw_document_upserts",)
    assert spark.tables[RAW_TABLE][0]["content"] == "new document"
    assert spark.tables[CHUNK_TABLE] == [old]

    writer.persist(plan)

    assert spark.tables[RAW_TABLE][0]["ingested_at"] == COMMIT_TIME
    assert [row["chunk_id"] for row in spark.tables[CHUNK_TABLE]] == ["new"]
    assert all(not (row["chunk_id"] == "old") for row in spark.tables[CHUNK_TABLE])


@pytest.mark.parametrize(
    ("table", "row", "key"),
    [
        (RAW_TABLE, _doc(), "doc_id"),
        (CHUNK_TABLE, _chunk(), "chunk_id"),
    ],
)
def test_writer_rejects_duplicate_target_keys_before_upsert(table, row, key):
    spark = FakeSpark()
    spark.tables[table] = [dict(row), dict(row)]
    plan = _plan([_doc()], [_chunk()] if key == "chunk_id" else ())

    with pytest.raises(DeltaPersistenceError, match=f"duplicate {key} values"):
        _writer(spark).persist(plan)

    assert len(spark.tables[table]) == 2
    assert not any(f"MERGE INTO {table} AS target" in statement for statement in spark.statements)
