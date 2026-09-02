from pathlib import Path
import sys
import os
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent

SRC_ROOT = PROJECT_ROOT / "src"

for candidate in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


@pytest.fixture(scope="session")
def catalog():
    """Return the catalog name from environment or default to lab5."""
    return os.environ.get("DATABRICKS_CATALOG", "dbr_dev")


@pytest.fixture(scope="session")
def bronze_schema():
    """Return the bronze schema name from environment or default to bronze."""
    return os.environ.get("DATABRICKS_BRONZE_SCHEMA", "ayyuborujzade_bronze")


@pytest.fixture(scope="session")
def silver_schema():
    """Return the silver schema name from environment or default to silver."""
    return os.environ.get("DATABRICKS_SILVER_SCHEMA", "ayyuborujzade_silver")


@pytest.fixture(scope="session")
def gold_schema():
    """Return the gold schema name from environment or default to gold."""
    return os.environ.get("DATABRICKS_GOLD_SCHEMA", "ayyuborujzade_gold")


@pytest.fixture(scope="session")
def spark():
    """Create one Databricks Connect session for enabled integration tests."""
    if os.environ.get("DATABRICKS_RUN_INTEGRATION", "0") != "1":
        pytest.skip("Integration tests are disabled; set DATABRICKS_RUN_INTEGRATION=1 to run them.")

    cluster_id = os.environ.get("DATABRICKS_CLUSTER_ID")
    if not cluster_id:
        pytest.skip("Set DATABRICKS_CLUSTER_ID to run Databricks Connect integration tests.")

    from databricks.connect import DatabricksSession

    return DatabricksSession.builder.remote(cluster_id=cluster_id).getOrCreate()
