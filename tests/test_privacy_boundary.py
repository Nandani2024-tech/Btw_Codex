from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import requests

from resurrect.core.databricks_client import DatabricksClient
from resurrect.handoff import build_handoff_manifest
from resurrect.parser import parse_telemetry
from resurrect.ui.console import StatusItem


def test_privacy_boundary_with_redacted_checkpoint(monkeypatch, tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "refs" / "entire" / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    fixture = Path(__file__).parent / "fixtures" / "redacted_checkpoint.jsonl"
    (checkpoint_dir / "checkpoint.jsonl").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    telemetry = parse_telemetry(checkpoint_dir)
    assert telemetry.error_signature
    assert not telemetry.status.is_complete
    assert telemetry.status.confidence == "partial"
    assert "prompt" in telemetry.status.missing_fields

    session = Mock(spec=requests.Session)
    response = Mock()
    response.raise_for_status.return_value = None
    session.post.return_value = response
    client = DatabricksClient("https://example.databricks.com", "token", "wh-1", session=session)

    result = client.query_failure_traps(telemetry)
    assert result.ok

    payload = session.post.call_args.kwargs["json"]
    assert "prompt" not in str(payload).lower()
    assert "[redacted]" not in str(payload).lower()
    assert "***" not in str(payload)
    assert "statement" in payload
    assert payload["statement"].startswith("SELECT * FROM dev_failure_traps")
    assert "parameters" in payload

    manifest = build_handoff_manifest(telemetry, verified_match=result.ok)
    assert manifest.status_label == "[PARTIAL / REDACTED CONTEXT]"
    assert manifest.confidence == "partial"
    assert manifest.is_complete is False

    item = StatusItem("Failure traps", result.ok, result.error or "", context_label=manifest.status_label)
    assert item.context_label == "[PARTIAL / REDACTED CONTEXT]"
