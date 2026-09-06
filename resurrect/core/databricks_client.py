"""Databricks connectivity helpers."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import requests


@dataclass(slots=True)
class DiagnosticResult:
    ok: bool
    latency_ms: float | None = None
    error: str | None = None


class DatabricksClient:
    def __init__(self, host: str | None, token: str | None, warehouse_id: str | None, session: requests.Session | None = None) -> None:
        self.host = host.rstrip("/") if host else None
        self.token = token
        self.warehouse_id = warehouse_id
        self.session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _post_statement(self, sql: str) -> requests.Response:
        url = f"{self.host}/api/2.0/sql/statements"
        payload: dict[str, Any] = {
            "warehouse_id": self.warehouse_id,
            "statement": sql,
            "wait_timeout": "10s",
        }
        return self.session.post(url, json=payload, headers=self._headers(), timeout=15)

    def ping_connection(self) -> DiagnosticResult:
        if not self.host:
            return DiagnosticResult(ok=False, error="Missing DATABRICKS_HOST.")
        if not self.token:
            return DiagnosticResult(ok=False, error="Missing DATABRICKS_TOKEN.")
        if not self.warehouse_id:
            return DiagnosticResult(ok=False, error="Missing DATABRICKS_WAREHOUSE_ID.")

        start = perf_counter()
        try:
            response = self._post_statement("SELECT 1")
            response.raise_for_status()
        except requests.RequestException as exc:
            return DiagnosticResult(ok=False, error=str(exc))
        latency_ms = (perf_counter() - start) * 1000
        return DiagnosticResult(ok=True, latency_ms=latency_ms)

    def verify_table_exists(self, table_name: str = "dev_failure_traps") -> DiagnosticResult:
        if not self.host or not self.token or not self.warehouse_id:
            return DiagnosticResult(ok=False, error="Databricks configuration is incomplete.")
        query = f"SELECT 1 FROM {table_name} LIMIT 1"
        try:
            response = self._post_statement(query)
            response.raise_for_status()
        except requests.RequestException as exc:
            return DiagnosticResult(ok=False, error=str(exc))
        return DiagnosticResult(ok=True)
