from __future__ import annotations

import json
from pathlib import Path

from resurrect.config import DEFAULT_DELTA_TABLE_NAME, ResurrectConfig


def test_loads_from_env_when_config_missing(tmp_path: Path) -> None:
    env = {
        "DATABRICKS_HOST": "https://example.databricks.com",
        "DATABRICKS_TOKEN": "token",
        "DATABRICKS_WAREHOUSE_ID": "wh-1",
    }
    config = ResurrectConfig.load(tmp_path, env=env)
    assert config.databricks_host == env["DATABRICKS_HOST"]
    assert config.databricks_token == env["DATABRICKS_TOKEN"]
    assert config.databricks_warehouse_id == env["DATABRICKS_WAREHOUSE_ID"]
    assert config.delta_table_name == DEFAULT_DELTA_TABLE_NAME


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    config = ResurrectConfig(
        databricks_host="https://example.databricks.com",
        databricks_token="token",
        databricks_warehouse_id="wh-1",
        delta_table_name="custom_table",
    )
    path = config.save(tmp_path)
    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["delta_table_name"] == "custom_table"

    loaded = ResurrectConfig.load(tmp_path, env={})
    assert loaded == config
