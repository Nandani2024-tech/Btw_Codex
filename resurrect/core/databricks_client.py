"""Databricks connectivity helpers."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import requests

from resurrect.parser import ParsedTelemetry


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

    def _post_statement(self, sql: str, parameters: list[dict[str, Any]] | None = None) -> requests.Response:
        url = f"{self.host}/api/2.0/sql/statements"
        payload: dict[str, Any] = {
            "warehouse_id": self.warehouse_id,
            "statement": sql,
            "wait_timeout": "10s",
        }
        if parameters:
            payload["parameters"] = parameters
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

    def query_failure_traps(self, telemetry: ParsedTelemetry, table_name: str = "dev_failure_traps") -> DiagnosticResult:
        if not self.host or not self.token or not self.warehouse_id:
            return DiagnosticResult(ok=False, error="Databricks configuration is incomplete.")
        if not telemetry.error_signature:
            return DiagnosticResult(ok=False, error="Missing sanitized error signature.")

        if telemetry.status.is_complete:
            statement = (
                f"SELECT * FROM {table_name} "
                "WHERE error_signature = :error_signature "
                "AND module_name IN (:module_0, :module_1, :module_2) "
                "LIMIT 5"
            )
            parameters = [{"name": "error_signature", "value": telemetry.error_signature}]
            parameters.extend({"name": f"module_{idx}", "value": module} for idx, module in enumerate(telemetry.module_names[:3]))
        else:
            statement = (
                f"SELECT * FROM {table_name} "
                "WHERE error_signature LIKE :error_signature "
                "OR module_name IN (:module_0, :module_1, :module_2) "
                "LIMIT 5"
            )
            parameters = [{"name": "error_signature", "value": f"%{telemetry.error_signature.split(':', 1)[0]}%"}]
            parameters.extend({"name": f"module_{idx}", "value": module} for idx, module in enumerate(telemetry.module_names[:3]))
        try:
            response = self._post_statement(statement, parameters=parameters)
            response.raise_for_status()
        except requests.RequestException as exc:
            return DiagnosticResult(ok=False, error=str(exc))
        suffix = "heuristic/partial" if not telemetry.status.is_complete else "verified"
        return DiagnosticResult(ok=True, error=suffix)
