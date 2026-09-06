from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import requests

from resurrect.core.databricks_client import DatabricksClient
from resurrect.core.entire_bridge import check_entire_status, setup_entire


def test_setup_entire_runs_commands(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    calls: list[list[str]] = []

    def fake_run(command, cwd=None, capture_output=None, text=None, check=None):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("resurrect.core.entire_bridge.subprocess.run", fake_run)
    result = setup_entire(cwd=tmp_path)
    assert result.ok
    assert calls == [["entire", "enable", "--force"], ["entire", "hooks", "configure", "--agent", "codex"]]


def test_check_entire_status_detects_active_checkpoints(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, cwd=None, capture_output=None, text=None, check=None):
        return SimpleNamespace(returncode=0, stdout="checkpoints active", stderr="")

    monkeypatch.setattr("resurrect.core.entire_bridge.subprocess.run", fake_run)
    result = check_entire_status(cwd=tmp_path)
    assert result.ok


def test_ping_connection_and_table_query(monkeypatch) -> None:
    session = Mock(spec=requests.Session)
    response = Mock()
    response.raise_for_status.return_value = None
    session.post.return_value = response
    client = DatabricksClient("https://example.databricks.com", "token", "wh-1", session=session)

    ping = client.ping_connection()
    table = client.verify_table_exists()

    assert ping.ok
    assert table.ok
    assert session.post.call_count == 2
    assert session.post.call_args_list[0].args[0].endswith("/api/2.0/sql/statements")


def test_ping_connection_reports_missing_fields() -> None:
    client = DatabricksClient(None, None, None)
    result = client.ping_connection()
    assert not result.ok
    assert "Missing DATABRICKS_HOST" in result.error
