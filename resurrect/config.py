"""Configuration loading and persistence for Agent Resurrect."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping


DEFAULT_DELTA_TABLE_NAME = "dev_failure_traps"


@dataclass(slots=True)
class ResurrectConfig:
    databricks_host: str | None = None
    databricks_token: str | None = None
    databricks_warehouse_id: str | None = None
    delta_table_name: str = DEFAULT_DELTA_TABLE_NAME

    @classmethod
    def load(cls, base_dir: Path | str = Path.cwd(), env: Mapping[str, str] | None = None) -> "ResurrectConfig":
        env_map = os.environ if env is None else env
        config_path = Path(base_dir) / ".resurrect" / "config.json"
        data: dict[str, Any] = {}
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
        return cls(
            databricks_host=data.get("databricks_host") or env_map.get("DATABRICKS_HOST"),
            databricks_token=data.get("databricks_token") or env_map.get("DATABRICKS_TOKEN"),
            databricks_warehouse_id=data.get("databricks_warehouse_id") or env_map.get("DATABRICKS_WAREHOUSE_ID"),
            delta_table_name=data.get("delta_table_name") or env_map.get("DELTA_TABLE_NAME") or DEFAULT_DELTA_TABLE_NAME,
        )

    def save(self, base_dir: Path | str = Path.cwd()) -> Path:
        config_dir = Path(base_dir) / ".resurrect"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return config_path

    def missing_fields(self) -> list[str]:
        missing = []
        if not self.databricks_host:
            missing.append("databricks_host")
        if not self.databricks_token:
            missing.append("databricks_token")
        if not self.databricks_warehouse_id:
            missing.append("databricks_warehouse_id")
        return missing
