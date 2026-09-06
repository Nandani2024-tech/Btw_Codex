from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from .parser import ParsedCheckpoint


@dataclass(frozen=True)
class LookupResult:
    query_mode: str
    statement_payload: dict[str, Any]
    status_label: str
    confidence: str
    response: dict[str, Any]


class DatabricksClient:
    """Minimal SQL Statements API client that sends only lookup metadata."""

    def __init__(
        self,
        host: str | None = None,
        token: str | None = None,
        warehouse_id: str | None = None,
    ) -> None:
        self.host = (host or os.environ.get("DATABRICKS_HOST", "")).rstrip("/")
        self.token = token or os.environ.get("DATABRICKS_TOKEN", "")
        self.warehouse_id = warehouse_id or os.environ.get("DATABRICKS_WAREHOUSE_ID", "")

    def build_statement_payload(self, checkpoint: ParsedCheckpoint) -> dict[str, Any]:
        """Construct a parameterized statement from the sanitized parser output only."""
        is_exact = checkpoint.lookup_mode == "exact"
        operator = "=" if is_exact else "LIKE"
        signature = checkpoint.error_signature if is_exact else f"{checkpoint.error_signature}%"
        return {
            "warehouse_id": self.warehouse_id,
            "statement": (
                "SELECT * FROM dev_failure_traps "
                f"WHERE error_signature {operator} :error_signature "
                "AND module_name = :module_0"
            ),
            "parameters": [
                {"name": "error_signature", "value": signature, "type": "STRING"},
                {"name": "module_0", "value": checkpoint.lookup_module, "type": "STRING"},
            ],
            "wait_timeout": "10s",
            "format": "JSON_ARRAY",
        }

    def lookup(self, checkpoint: ParsedCheckpoint) -> LookupResult:
        payload = self.build_statement_payload(checkpoint)
        response = self._post_statement(payload)
        has_rows = bool(response.get("result", {}).get("data_array"))
        verified = checkpoint.is_complete and has_rows and response.get("status", {}).get("state") == "SUCCEEDED"
        return LookupResult(
            query_mode=checkpoint.lookup_mode,
            statement_payload=payload,
            status_label="verified" if verified else "partial",
            confidence="verified" if verified else "heuristic",
            response=response,
        )

    def _post_statement(self, payload: dict[str, Any]) -> dict[str, Any]:
        missing = [
            name
            for name, value in (
                ("DATABRICKS_HOST", self.host),
                ("DATABRICKS_TOKEN", self.token),
                ("DATABRICKS_WAREHOUSE_ID", self.warehouse_id),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        req = request.Request(
            f"{self.host}/api/2.0/sql/statements",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Databricks HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Databricks connection failed: {exc}") from exc
