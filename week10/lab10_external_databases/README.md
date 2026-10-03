# Lab 10 — External Operational Databases

This lab demonstrates Lakehouse Federation to PostgreSQL through Neon and
incremental change processing with Delta Change Data Feed (CDF). The work was
validated in the Databricks Free/DEV workspace; no Academy workspace or
credentials are part of these artifacts.

## Lakehouse Federation

Federation queries an external database through a Unity Catalog foreign catalog
without first copying its tables into Delta. In this lab, the existing
connection `lab10_postgres` and foreign catalog `lab10_postgres_catalog`
expose `public.customers` and `public.orders`. Their setup is intentionally
not repeated here because it requires workspace-managed connection details.

[`federation.sql`](federation.sql) queries both foreign tables, creates a Delta
copy of customers at `workspace.default.lab10_customers_delta`, compares row
counts, and joins the foreign customer rows to that copy. Validation confirmed
that the foreign and Delta customer counts were both 5 and the join succeeded.

Federation reads current source data when a query runs, so it avoids a scheduled
copy's freshness lag. It can have more query latency because data access
depends on the remote database and network. Ingestion instead stores a local
Delta copy: it may be stale between refreshes, but repeated analytics can run
against the local table.

### Security considerations

Keep database credentials in the workspace-managed connection, grant the
least privileges needed (read-only for federation when sufficient), protect
network access, and grant foreign-catalog access only to intended users. Do
not put passwords or tokens in notebooks, SQL files, or source control.

## Delta Change Data Feed

[`cdc.sql`](cdc.sql) creates `workspace.default.lab10_customers_cdc` with CDF
enabled, snapshots its initial rows into
`workspace.default.lab10_customers_target`, simulates the supplied changes,
inspects `table_changes()`, and uses `MERGE INTO` to apply the latest change
per customer. The initial validated source contained customers 1–5. The
original values for every seed row were not included in the handoff, so load
the original validated seed data at the marked step before creating the
target snapshot; the artifact deliberately does not invent missing values.

The simulated changes are customer 6 inserted (John Miller, Spain, Consumer),
customer 2 updated to Mark Smith, Germany, Corporate, customer 5 deleted
(Emma Davis), and customer 2 updated again from Corporate to Consumer. CDF
inspection verified `insert`, `update_preimage`, `update_postimage`, and
`delete`, along with `_commit_version` and `_commit_timestamp`.

The final target was verified as:

| Customer ID | Name | Country | Segment |
|---:|---|---|---|
| 1 | Alice Johnson | Poland | Consumer |
| 2 | Mark Smith | Germany | Consumer |
| 3 | Sofia Brown | Poland | Consumer |
| 4 | Daniel Wilson | France | Corporate |
| 6 | John Miller | Spain | Consumer |

Batch ingestion periodically copies a snapshot or a selected range of source
data. CDC applies changes as they occur or as they are delivered, reducing the
amount of data repeatedly processed. CDF is a Delta mechanism for reading
committed row changes; CDC is the broader change-capture pattern. SCD describes
how a target models history: for example, CDC events can maintain an SCD Type 1
current-state table or feed an SCD Type 2 history table.

Late-arriving changes need an explicit policy. Use commit versions to process
Delta changes in a stable order, retain a checkpoint of the last applied
version for recurring batches, and use business event timestamps and
deduplication rules when source events arrive late or out of order. The
training merge starts at version 0 to apply this lab's available history; a
production incremental process should resume from its persisted checkpoint.

## Files

- `federation.sql` — foreign-table queries, Delta copy, counts, and join.
- `cdc.sql` — CDF source setup, change simulation, CDF inspection, merge, and
  consistency checks.
- `README.md` — concepts, validation notes, and usage context.
