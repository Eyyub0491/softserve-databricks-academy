from pathlib import Path
import sys
import os
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"

for candidate in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


# Environment fixtures for parameterized table references
@pytest.fixture(scope="session")
def catalog():
    """Return the catalog name from environment or default to lab5."""
    return os.environ.get("DATABRICKS_CATALOG", "lab5")


@pytest.fixture(scope="session")
def bronze_schema():
    """Return the bronze schema name from environment or default to bronze."""
    return os.environ.get("DATABRICKS_BRONZE_SCHEMA", "bronze")


@pytest.fixture(scope="session")
def silver_schema():
    """Return the silver schema name from environment or default to silver."""
    return os.environ.get("DATABRICKS_SILVER_SCHEMA", "silver")


@pytest.fixture(scope="session")
def gold_schema():
    """Return the gold schema name from environment or default to gold."""
    return os.environ.get("DATABRICKS_GOLD_SCHEMA", "gold")
