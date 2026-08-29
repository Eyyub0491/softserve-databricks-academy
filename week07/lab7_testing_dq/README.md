# Lab 7: Testing & Data Quality

## Part A: Unit Testing

Pure Python unit tests for transformation logic extracted from Lab 5 (Silver) and Lab 6 (Gold) pipelines.

### Structure

```
lab7_testing_dq/
├── src/
│   └── transformations/
│       ├── string_utils.py       # String normalization functions
│       ├── date_utils.py         # Timestamp parsing functions
│       ├── business_logic.py     # Business rule transformations
│       └── validation.py         # Data validation functions
├── tests/
│   └── unit/
│       ├── test_string_utils.py
│       ├── test_date_utils.py
│       ├── test_business_logic.py
│       └── test_validation.py
├── requirements.txt
└── README.md
```

### Functions Tested

1. **normalize_customer_name** (`string_utils.py`)
   - Based on: Lab 5 `silver_pipeline.py` line 24
   - Logic: `F.initcap(F.trim(...))`

2. **parse_unix_timestamp** (`date_utils.py`)
   - Based on: Lab 5 `silver_pipeline.py` lines 36-38
   - Logic: `F.to_timestamp(F.from_unixtime(...))`

3. **map_loyalty_segment** (`business_logic.py`)
   - Based on: Lab 6 `dim_customers` CASE statement
   - Logic: Maps 0-3 to None/Bronze/Silver/Gold

4. **calculate_line_total_with_discount** (`business_logic.py`)
   - Based on: Lab 6 `fct_sales_orders` revenue calculations
   - Logic: Converts cents to dollars, applies discount

5. **validate_loyalty_segment** (`validation.py`)
   - Based on: Lab 5/6 loyalty segment business rules
   - Logic: Validates segment is in [0-3] range

### Running Tests

```bash
# From Databricks workspace file system
cd /Workspace/Users/ayyub.orujzada@gmail.com/week07/lab7_testing_dq

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=src/transformations --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_string_utils.py -v
```

### Test Coverage

- **Normal cases**: Standard valid inputs
- **NULL/None cases**: Handling of missing values
- **Edge cases**: Empty strings, boundary values, invalid inputs
- **Error cases**: Expected exceptions for invalid data

### Notes

- All functions are pure Python (no PySpark dependencies)
- Tests can run locally or in CI/CD pipelines
- Surrogate key generation (SQL HASH) is NOT tested - Python hash() is not reproducible
- Original Lab 5/6 pipelines remain unchanged

---

## Part B — Local Data Quality Framework

This project now includes a small local DQ framework under `dq/` for generic, pure-Python checks that can later be reused with Spark or Databricks results.

### Included checks

- Completeness: null/empty required fields
- Uniqueness: duplicate detection for single or composite keys
- Validity: accepted values and numeric ranges
- Referential integrity: child key must exist in parent collection
- Freshness: timestamp must be within a configurable maximum age
- Reconciliation: row counts and numeric aggregates compared with tolerance

### Structure

```text
lab7_testing_dq/
├── dq/
│   ├── __init__.py
│   └── checks.py
├── tests/
│   └── unit/
│       └── test_dq_checks.py
├── src/
│   └── transformations/
├── requirements.txt
├── README.md
└── .gitignore
```

### Running the DQ tests

```bash
cd week07/lab7_testing_dq
pytest tests/unit/ -v
```

### Notes

- These checks are intentionally generic and do not hard-code Lab 5/6 table names.
- They are designed to be simple, deterministic, and easy to explain during an Academy review.
- Databricks/Spark-specific execution and table metadata checks remain out of scope for this local-only stage.