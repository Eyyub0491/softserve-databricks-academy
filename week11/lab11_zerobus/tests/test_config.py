import pytest
from unittest.mock import Mock

from src.config import (
    DEFAULT_CLIENT_ID,
    DEFAULT_SECRET_KEY,
    DEFAULT_SECRET_SCOPE,
    ZerobusConfig,
)


def _dbutils(secret="test-secret"):
    fake = Mock()
    fake.secrets.get.return_value = secret
    return fake


def test_config_uses_confirmed_free_defaults_and_reads_secret_from_dbutils():
    dbutils = _dbutils()
    config = ZerobusConfig.from_env({}, dbutils=dbutils)
    assert config.endpoint == "https://7474657415962864.zerobus.us-east-2.cloud.databricks.com"
    assert config.host == "https://dbc-f7231d90-d8a3.cloud.databricks.com"
    assert config.client_id == DEFAULT_CLIENT_ID
    assert config.client_secret == "test-secret"
    assert config.table_name == "lab5.default.lab11_events"
    dbutils.secrets.get.assert_called_once_with(scope=DEFAULT_SECRET_SCOPE, key=DEFAULT_SECRET_KEY)


def test_config_accepts_endpoint_without_scheme():
    config = ZerobusConfig.from_env({
        "ZEROBUS_CLIENT_ID": "test-id",
        "ZEROBUS_ENDPOINT": "example.zerobus.us-east-2.cloud.databricks.com",
    }, dbutils=_dbutils())
    assert config.endpoint.startswith("https://")


def test_config_allows_workspace_and_table_overrides():
    config = ZerobusConfig.from_env({
        "DATABRICKS_HOST": "https://custom-workspace.cloud.databricks.com/",
        "DATABRICKS_WORKSPACE_ID": "123456789",
        "ZEROBUS_ENDPOINT": "https://custom-endpoint.example",
        "ZEROBUS_CLIENT_ID": "custom-client-id",
        "ZEROBUS_CATALOG": "other_catalog",
        "ZEROBUS_SCHEMA": "other_schema",
        "ZEROBUS_TABLE": "other_table",
    }, dbutils=_dbutils())
    assert config.host == "https://custom-workspace.cloud.databricks.com"
    assert config.workspace_id == "123456789"
    assert config.endpoint == "https://custom-endpoint.example"
    assert config.client_id == "custom-client-id"
    assert config.table_name == "other_catalog.other_schema.other_table"


def test_config_requires_databricks_secret_provider_without_secret_env_fallback():
    with pytest.raises(ValueError, match="dbutils is required"):
        ZerobusConfig.from_env({"ZEROBUS_CLIENT_SECRET": "must-not-be-used"})


def test_config_reports_secret_lookup_failure_without_leaking_exception():
    dbutils = _dbutils()
    dbutils.secrets.get.side_effect = RuntimeError("secret contents must not escape")
    with pytest.raises(ValueError, match="Could not read the Zerobus client secret") as error:
        ZerobusConfig.from_env({}, dbutils=dbutils)
    assert "secret contents" not in str(error.value)


def test_config_repr_does_not_expose_secret():
    config = ZerobusConfig.from_env({}, dbutils=_dbutils("sensitive-placeholder"))
    assert "sensitive-placeholder" not in repr(config)


def test_config_rejects_blank_client_id():
    with pytest.raises(ValueError, match="ZEROBUS_CLIENT_ID"):
        ZerobusConfig.from_env({"ZEROBUS_CLIENT_ID": " "}, dbutils=_dbutils())
