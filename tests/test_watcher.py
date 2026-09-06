from __future__ import annotations

from dataclasses import replace
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from resurrect.parser import ContextStatus, ParsedTelemetry
import resurrect.watcher as watcher


class FakeProcess:
    def __init__(self) -> None:
        self.stdout = StringIO("agent starting\n")
        self.returncode = None
        self.terminated = False
        self.killed = False
        self._polls = 0

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


def test_watch_agent_trips_breaker_and_writes_manifest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    process = FakeProcess()
    monkeypatch.setattr(watcher.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(watcher.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(watcher, "_latest_checkpoint_source", lambda cwd: tmp_path / "refs" / "entire" / "checkpoints")

    telemetry = ParsedTelemetry(
        error_signature="RuntimeError: redacted failure",
        module_names=["watcher"],
        privacy_provenance="checkpoint",
        status=ContextStatus(is_complete=False, confidence="partial", missing_fields=["prompt"]),
        source_path=tmp_path / "refs" / "entire" / "checkpoints" / "checkpoint.jsonl",
    )
    states = [telemetry, telemetry, telemetry]

    def fake_parse_telemetry(*_args, **_kwargs):
        return states.pop(0) if states else telemetry

    monkeypatch.setattr(watcher, "parse_telemetry", fake_parse_telemetry)
    monkeypatch.setattr(
        watcher.DatabricksClient,
        "fetch_resolution",
        lambda self, error_signature, module_name=None: {
            "resolution": "restart the worker",
            "commit": "abc1234",
            "confidence": "verified",
        },
    )

    result = watcher.watch_agent(["pytest", "-q"], max_failures=3, poll_interval=0.0)

    assert result.failures >= 3
    assert process.terminated
    assert result.manifest_path is not None
    assert result.manifest_path.exists()
    assert result.resolution["commit"] == "abc1234"
