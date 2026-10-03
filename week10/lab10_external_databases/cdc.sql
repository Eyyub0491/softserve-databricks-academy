-- Lab 10B: Delta Change Data Feed (CDF) and incremental target maintenance.
-- Run the setup/target snapshot before applying the simulated changes.

-- Create the source with CDF enabled from its first data changes.
CREATE TABLE IF NOT EXISTS workspace.default.lab10_customers_cdc (
  customer_id INT,
  customer_name STRING,
  country STRING,
  segment STRING
)
TBLPROPERTIES (delta.enableChangeDataFeed = true);

-- Load the validated initial customer rows 1-5 into the source here, using the
-- lab's original seed data. Its full initial field values are intentionally
-- not reconstructed in this artifact.

-- Take the target snapshot before simulating changes.
CREATE TABLE IF NOT EXISTS workspace.default.lab10_customers_target
AS
SELECT customer_id, customer_name, country, segment
FROM workspace.default.lab10_customers_cdc;

-- Simulate the validated changes.
INSERT INTO workspace.default.lab10_customers_cdc
  (customer_id, customer_name, country, segment)
VALUES
  (6, 'John Miller', 'Spain', 'Consumer');

UPDATE workspace.default.lab10_customers_cdc
SET customer_name = 'Mark Smith',
    country = 'Germany',
    segment = 'Corporate'
WHERE customer_id = 2;

-- Remove customer 5 (Emma Davis).
DELETE FROM workspace.default.lab10_customers_cdc
WHERE customer_id = 5;

UPDATE workspace.default.lab10_customers_cdc
SET segment = 'Consumer'
WHERE customer_id = 2;

-- Inspect row-level changes and their Delta commit metadata.
SELECT
  customer_id,
  customer_name,
  country,
  segment,
  _change_type,
  _commit_version,
  _commit_timestamp
FROM table_changes('workspace.default.lab10_customers_cdc', 0)
ORDER BY _commit_version, customer_id, _change_type;

-- Apply each customer's latest insert, postimage, or delete to the target.
-- Preimages are excluded; commit version determines the latest event.
MERGE INTO workspace.default.lab10_customers_target AS target
USING (
  SELECT customer_id, customer_name, country, segment, _change_type
  FROM table_changes('workspace.default.lab10_customers_cdc', 0)
  WHERE _change_type IN ('insert', 'update_postimage', 'delete')
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id
    ORDER BY _commit_version DESC
  ) = 1
) AS changes
ON target.customer_id = changes.customer_id
WHEN MATCHED AND changes._change_type = 'delete' THEN DELETE
WHEN MATCHED THEN UPDATE SET
  target.customer_name = changes.customer_name,
  target.country = changes.country,
  target.segment = changes.segment
WHEN NOT MATCHED AND changes._change_type <> 'delete' THEN INSERT (
  customer_id, customer_name, country, segment
) VALUES (
  changes.customer_id, changes.customer_name, changes.country, changes.segment
);

-- Compare source and target row counts after the merge.
SELECT 'source' AS table_name, COUNT(*) AS row_count
FROM workspace.default.lab10_customers_cdc
UNION ALL
SELECT 'target' AS table_name, COUNT(*) AS row_count
FROM workspace.default.lab10_customers_target;

-- Return any rows present on one side but not the other; an empty result means
-- the source and target are consistent.
SELECT * FROM (
  SELECT customer_id, customer_name, country, segment
  FROM workspace.default.lab10_customers_cdc
  EXCEPT
  SELECT customer_id, customer_name, country, segment
  FROM workspace.default.lab10_customers_target
)
UNION ALL
SELECT * FROM (
  SELECT customer_id, customer_name, country, segment
  FROM workspace.default.lab10_customers_target
  EXCEPT
  SELECT customer_id, customer_name, country, segment
  FROM workspace.default.lab10_customers_cdc
);

-- Expected validated target snapshot: customers 1, 2, 3, 4, and 6.
SELECT customer_id, customer_name, country, segment
FROM workspace.default.lab10_customers_target
ORDER BY customer_id;
