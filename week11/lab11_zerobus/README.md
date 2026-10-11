# Lab 11 — Zero-Bus Streaming with Zerobus

## 1. Lab Objective

Implement event-driven pipelines **without a centralized message-bus layer** using Databricks Zerobus Ingest. A producer pushes events directly into a Unity Catalog Delta table, and a separate idempotent processing layer deduplicates re-delivered events by business key.

Lab 11 requirements covered:

1. Build a producer and route events directly to a UC Delta table via Zerobus.
2. Implement idempotent processing.
3. Compare Kafka-style architecture with the zero-bus approach.
4. Discuss event-driven pipelines, decoupled systems, cost and operational trade-offs.
5. Done when events are pushed directly into a UC Delta table and the design is compared against a bus-based alternative.

## 2. Architecture

```
Producer (producer.py)
  ↓  gRPC / JSON records
Databricks Zerobus Ingest (serverless endpoint)
  ↓  auto-scaling, write-ahead log, batch commit
Unity Catalog Delta raw table: lab5.default.lab11_events
  ↓  MERGE with ROW_NUMBER() deduplication
Unity Catalog Delta dedup table: lab5.default.lab11_events_dedup
```

**Two layers:**

* **Raw ingestion** — the producer sends JSON records through the Zerobus SDK. Zerobus writes them directly into a managed Delta table. Duplicate physical rows are expected (re-delivery is normal); the raw table preserves the full ingestion history.
* **Idempotent processing** — a MERGE statement reads the raw table, deduplicates by `event_id` using `ROW_NUMBER()`, and upserts one logical row per event into a separate Delta table. This is safe to run repeatedly.

## 3. Why Zerobus is "Zero-Bus"

Traditional streaming architectures insert a message broker (Kafka, Pulsar, Kinesis) between producers and the lakehouse. Zerobus removes that middle layer entirely — the producer pushes data straight into a Unity Catalog Delta table through a serverless, auto-scaling endpoint. There are no brokers to provision, partitions to manage, or consumer groups to configure. The workflow is two steps: create a table, then push data to it.

## 4. Producer Implementation

**File:** `producer.py`

The producer uses the `databricks-zerobus-ingest-sdk` Python package (import name: `zerobus`).

Key function:

```python
run_producer(dbutils=dbutils, count=5, start=0)
```

Flow:

1. Read OAuth `client_id` and `client_secret` from Databricks Secrets at runtime.
2. Initialise `ZerobusSdk(host=<zerobus_endpoint>, unity_catalog_url=<workspace_url>)`.
3. Create a `TableProperties` for the target table (JSON record format).
4. Open a gRPC stream via `sdk.create_stream(client_id=..., client_secret=..., table_properties=...)`.
5. For each event: serialise to JSON and call `stream.ingest_record_offset(payload)`.
6. Wait for all acknowledgments with `stream.wait_for_offset(last_offset)`.
7. Flush and close the stream.

The `zerobus` import is lazy (inside `run_producer`) so the module can be imported in local test environments without the SDK installed.

## 5. Authentication / Security

* **OAuth client credentials:** A dedicated Databricks service principal (`lab11-zerobus-producer`) was created in the Free workspace. The service principal has an OAuth client secret generated via the Databricks API.
* **Databricks Secrets:** The `client_id` and `client_secret` are stored in a Databricks secret scope named `lab11_zerobus`. The producer reads them at runtime via `dbutils.secrets.get(scope="lab11_zerobus", key="client_secret")`.
* **No secret in source code:** No OAuth token, client secret, or password appears in any source file, SQL file, notebook, or README. The producer code contains only the secret **scope name** and **key name** — never the values.
* **Minimum UC privileges:** The service principal has only `USE CATALOG`, `USE SCHEMA`, `SELECT`, and `MODIFY` on the target table. No admin or broad privileges.


## 5b. Configuration

Public connection and table settings are defined as constants in `producer.py`:

| Constant | Purpose |
| --- | --- |
| `TABLE_NAME` | Raw target table (default `lab5.default.lab11_events`) |
| `SECRET_SCOPE` | Databricks secret scope name (default `lab11_zerobus`) |

The producer reads OAuth credentials only from `dbutils.secrets.get(scope="lab11_zerobus", key="client_secret")`. No secret is read from environment variables or source files.

## 6. Event Schema

| Column | Type | Description |
| --- | --- | --- |
| `event_id` | STRING | Business/event identifier (idempotency key) |
| `event_type` | STRING | Event type (e.g. `order_created`, `user_signup`) |
| `event_time` | TIMESTAMP | Event timestamp |
| `producer_id` | STRING | Producer identifier |
| `payload` | STRING | JSON-encoded event payload |

## 7. Timestamp Encoding

**Zerobus expects `TIMESTAMP` as `int64` epoch microseconds, not a string.**

Sending ISO 8601 strings (e.g. `2026-10-07T20:05:39.907Z`) or formatted date strings (e.g. `2026-10-07 20:05:39`) causes a server-side decoding error:

```
NonRetriableException: Record decoder/encoder error: invalid digit found in string
```

The producer converts to epoch microseconds:

```python
int(datetime.now(timezone.utc).timestamp() * 1_000_000)
```

This is documented in the [Zerobus supported data types](https://docs.databricks.com/aws/en/ingestion/zerobus-concepts/) — `TIMESTAMP` maps to `int64` (epoch time in microseconds). Similarly, `DATE` maps to `int32` (days since epoch).

## 8. Idempotency Design

**File:** `idempotency.py`

Zerobus does **not** deduplicate events by business key. If the producer re-sends the same `event_id`, the raw table will contain duplicate physical rows. Idempotency is implemented in a separate processing layer:

* **`event_id` is the idempotency key** — one logical event per `event_id`.
* **Raw table preserves ingestion history** — duplicate rows are never deleted from `lab11_events`.
* **`ROW_NUMBER()` / `MERGE`** — the source query deduplicates raw rows by `event_id`, keeping the most recent delivery (`ORDER BY event_time DESC`). The MERGE upserts into the dedup table using `event_id` as the merge key.
* **Safe to re-run** — `WHEN MATCHED THEN UPDATE` / `WHEN NOT MATCHED THEN INSERT` ensures re-processing with no new events is a no-op.

```sql
MERGE INTO lab5.default.lab11_events_dedup AS target
USING (
  SELECT event_id, event_type, event_time, producer_id, payload
  FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY event_time DESC) AS rn
    FROM lab5.default.lab11_events
  ) WHERE rn = 1
) AS source
ON target.event_id = source.event_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
```

## 9. Actual Validation Results

All results from real Zerobus ingestion in the Free Databricks workspace (AWS us-east-2).

| Step | Raw rows | Raw distinct IDs | Dedup rows | Dedup distinct IDs |
| --- | --- | --- | --- | --- |
| First ingestion (5 events) | 5 | 5 | — | — |
| Re-send same 5 events | 10 | 5 | — | — |
| Idempotent processing (pass 1) | 10 | 5 | 5 | 5 |
| Idempotent processing (pass 2, no new events) | 10 | 5 | 5 | 5 |

Key findings:

* 5 events ingested successfully through Zerobus in 0.6 seconds.
* Re-sending the same 5 event IDs created 5 duplicate physical rows (10 total, 5 distinct).
* Zerobus confirmed: **does not deduplicate by business key**.
* First MERGE pass: 10 raw rows → 5 dedup rows (one per `event_id`).
* Second MERGE pass: dedup table still 5 rows — idempotency demonstrated.

## 10. Kafka vs Zerobus Comparison

### Kafka-style architecture

```
Producer
  ↓
Kafka broker / topic
  ↓
partitions (with replication)
  ↓
consumer group / consumers
  ↓
stream processing or ingestion application
  ↓
Delta / lakehouse
```

### Zero-bus (Zerobus) architecture

```
Producer
  ↓
Databricks Zerobus Ingest (serverless)
  ↓
Unity Catalog Delta table
```

### Kafka advantages

* **Decoupling producers and consumers** — producers and consumers evolve independently.
* **Multiple independent consumers** — several downstream systems can read the same stream.
* **Fan-out** — one event can be routed to many downstream systems.
* **Partition-based scaling** — throughput scales horizontally with partitions.
* **Replay / offset-based consumption** — consumers can re-read from a specific offset.
* **Broad ecosystem** — Kafka Connect, Kafka Streams, schema registry, and a large community.
* **Organisational platform** — when Kafka is already the event backbone, adding a new producer is low-friction.

### Kafka disadvantages

* **Broker infrastructure** — provisioning, tuning, and maintaining Kafka clusters.
* **Partitions and replication management** — partition rebalancing, replica placement, ISR monitoring.
* **Consumer management** — consumer group coordination, lag monitoring, offset commits.
* **Operational overhead** — monitoring, alerting, security, upgrades.
* **Additional infrastructure and potentially higher cost** — the broker layer adds compute, storage, and networking costs.

### Zerobus advantages

* **No message-broker layer** — the producer pushes directly to the lakehouse.
* **Direct lakehouse ingestion** — data lands in a governed Delta table with no intermediate system.
* **Simpler Databricks-centric architecture** — fewer moving parts, less glue code.
* **Less infrastructure to operate** — no brokers, partitions, or consumer groups.
* **Serverless push-based ingestion** — auto-scales with load, no capacity planning.
* **Potentially lower operational overhead** — no broker ops team needed.

### Zerobus limitations

* **Destination is the lakehouse/Delta** — Zerobus writes to a Delta table, not a general-purpose event bus.
* **Less suitable for many independent consumers** — if multiple systems need the same raw event stream, a message bus provides better fan-out semantics.
* **Does not replace Kafka's general-purpose event-bus role** — Kafka serves use cases beyond lakehouse ingestion (microservice communication, CDC distribution, real-time fan-out).
* **Business-key idempotency is the processing layer's responsibility** — Zerobus does not deduplicate by business key; the consumer must implement MERGE/dedup logic.
* **Replay / fan-out semantics differ** — there are no consumer offsets or partition-based replay; re-processing relies on re-reading the Delta table.

## 11. Cost and Operational Trade-offs

| Dimension | Kafka + ingestion job | Zerobus |
| --- | --- | --- |
| Infrastructure | Broker cluster(s), storage, networking | None (serverless) |
| Operational team | Kafka ops + ingestion app maintainer | Minimal — Databricks manages the endpoint |
| Scaling | Manual partition planning or auto-scaling config | Automatic serverless scaling |
| Consumer fan-out | Native (multiple consumer groups) | Not native — re-read Delta table or add a separate bus |
| Idempotency | Consumer-side or Kafka Streams | Processing-layer MERGE (this lab) |
| Replay | Offset-based, from any point in time | Re-query Delta table (time travel) |
| Cost model | Always-on broker compute + storage + ingestion compute | Pay per ingestion volume (serverless) |
| Best fit | Multi-consumer event distribution, org-wide event backbone | Direct-to-lakehouse streaming, IoT/telemetry, single-destination pipelines |

These are architecture-dependent trade-offs — neither approach is universally cheaper, faster, or more scalable. The right choice depends on the number of consumers, the need for fan-out, existing infrastructure, and team expertise.

## 12. Limitations / When Kafka is Preferable

Zerobus is **not a replacement for Kafka** in all scenarios. Kafka is preferable when:

* **Multiple independent consumers** need the same event stream (e.g. real-time fraud detection + audit logging + notification service).
* **Fan-out to multiple downstream systems** is a core requirement.
* **Offset-based replay** is needed (re-process events from a specific point).
* **Kafka is already the organisational platform** — adding Zerobus would introduce a parallel ingestion path.
* **Non-lakehouse destinations** are required (e.g. a microservice reads from Kafka, not from Delta).
* **Complex stream processing** is needed before landing in the lakehouse (e.g. Kafka Streams, Flink).

Zerobus is preferable when:

* The destination is the Databricks lakehouse and a single Delta table is sufficient.
* You want to minimise infrastructure and operational overhead.
* The producer can push data directly (push-based model fits the workload).
* Event volume is variable and serverless auto-scaling is attractive.

## 13. How to Run / Test Locally

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run the local test suite

```bash
cd week11/lab11_zerobus
python -m pytest tests -q
```

Tests mock the Zerobus SDK and Spark, so they run without Databricks credentials or the `zerobus` package.

### Run in Databricks (Free workspace)

1. Install the SDK: `pip install databricks-zerobus-ingest-sdk`
2. Ensure the secret scope `lab11_zerobus` has keys `client_id` and `client_secret`.
3. Run the table DDL: `sql/create_tables.sql`
4. Ingest events:

```python
from producer import run_producer
run_producer(dbutils=dbutils, count=5, start=0)
```

5. Deduplicate:

```python
from idempotency import run_idempotent_processing
run_idempotent_processing(spark)
```

## 14. What Was Actually Tested in Free vs What Is Mocked Locally

| Test | Free workspace (real) | Local (mocked) |
| --- | --- | --- |
| Service principal creation | ✅ Real SP created via SCIM API | N/A |
| OAuth secret generation | ✅ Real OAuth secret via workspace API | N/A |
| Secret stored in Databricks Secrets | ✅ Real secret scope | N/A |
| UC privileges granted | ✅ Real GRANT statements | N/A |
| Zerobus ingestion (5 events) | ✅ Real gRPC stream to Zerobus endpoint | Mocked zerobus SDK |
| Timestamp as epoch microseconds | ✅ Real Delta TIMESTAMP conversion | Event structure verified |
| Raw table duplicate detection | ✅ Real 10 rows / 5 distinct IDs | N/A |
| Idempotent MERGE (pass 1) | ✅ Real MERGE → 5 dedup rows | MERGE SQL structure verified |
| Idempotent MERGE (pass 2) | ✅ Real re-run → still 5 rows | Re-run safety verified by mock |
| Event structure / payload JSON | ✅ Real query + from_json validation | ✅ Unit tested |
| Credential handling | ✅ Real dbutils.secrets.get | ✅ Mocked dbutils |
| Stream lifecycle (open/close) | ✅ Real stream open + close | ✅ Mocked stream, close verified |

## File Structure

```
week11/lab11_zerobus/
├── producer.py              # Zerobus producer (pushes events to Delta)
├── idempotency.py           # Idempotent MERGE processing layer
├── sql/create_tables.sql    # DDL for raw and dedup tables
├── tests/
│   ├── __init__.py
│   └── unit/
│       ├── __init__.py
│       ├── test_producer.py      # 16 tests for producer
│       └── test_idempotency.py    # 12 tests for idempotency
├── requirements.txt
├── pytest.ini
└── README.md
```