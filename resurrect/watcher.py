"""Live agent watcher and circuit-breaker loop for resurrect run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import time
import threading
from typing import Callable, Iterable

from resurrect.config import ResurrectConfig
from resurrect.core.databricks_client import DatabricksClient
from resurrect.handoff import write_handoff_manifest
from resurrect.parser import ParsedTelemetry, parse_telemetry
from resurrect.ui.console import render_breaker_trip_panel


@dataclass(slots=True)
class WatchResult:
    ok: bool
    failures: int
    tokens_intercepted: int
    telemetry: ParsedTelemetry
    resolution: dict[str, object]
    manifest_path: Path | None = None
    status_line: str = ""


def _default_checkpoint_dir(cwd: Path) -> Path:
    return cwd / "refs" / "entire" / "checkpoints"


def _latest_checkpoint_source(cwd: Path) -> Path:
    checkpoint_root = _default_checkpoint_dir(cwd)
    git_dir = cwd / ".git"
    if git_dir.exists():
        try:
            ref = subprocess.run(
                [
                    "git",
                    "for-each-ref",
                    "--sort=-committerdate",
                    '--format=%(refname)',
                    "refs/entire/checkpoints/",
                ],
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=10,
            )
            latest_ref = next((line.strip() for line in (ref.stdout or "").splitlines() if line.strip()), "")
            if latest_ref:
                show = subprocess.run(
                    ["git", "show", f"{latest_ref}:0/full.jsonl"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    timeout=10,
                )
                if show.returncode == 0 and (show.stdout or "").strip():
                    tmp = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".jsonl")
                    try:
                        tmp.write(show.stdout)
                        tmp.flush()
                    finally:
                        tmp.close()
                    return Path(tmp.name)
        except (OSError, subprocess.SubprocessError):
            pass

    if checkpoint_root.exists():
        return checkpoint_root
    local_entire = cwd / ".entire"
    if local_entire.exists():
        return local_entire
    return checkpoint_root


def _stream_output(process: subprocess.Popen[str], on_chunk: Callable[[str], None] | None = None) -> None:
    if process.stdout is None:
        return
    for line in iter(process.stdout.readline, ""):
        if not line:
            break
        print(line, end="")
        if on_chunk is not None:
            on_chunk(line)


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _estimate_tokens(texts: Iterable[str]) -> int:
    total_chars = sum(len(text) for text in texts if text)
    return max(1, total_chars // 4) if total_chars else 0


def _normalize_command(command: list[str] | str) -> list[str] | str:
    if isinstance(command, str):
        return command
    if not command:
        return command
    if os.name == "nt":
        resolved = shutil.which(command[0])
        if resolved:
            return [resolved, *command[1:]]
    return command


def watch_agent(command: list[str] | str, max_failures: int = 3, poll_interval: float = 2.0) -> WatchResult:
    cwd = Path.cwd()
    normalized = _normalize_command(command)
    popen_kwargs: dict[str, object] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if isinstance(normalized, str):
        popen_kwargs["shell"] = True
    elif os.name == "nt":
        popen_kwargs["shell"] = True

    try:
        process = subprocess.Popen(normalized, **popen_kwargs)
    except FileNotFoundError:
        missing = command[0] if isinstance(command, list) and command else str(command).split()[0]
        print(
            f"[bold red]Command not found:[/bold red] {missing}. "
            "Please verify the tool is installed and available in your PATH."
        )
        return WatchResult(
            ok=False,
            failures=0,
            tokens_intercepted=0,
            telemetry=ParsedTelemetry(),
            resolution={"resolution": "", "commit": None, "confidence": "heuristic"},
            status_line="command-not-found",
        )

    failures = 0
    tokens_intercepted = 0
    last_signature = ""
    telemetry = ParsedTelemetry()
    checkpoint_source = _latest_checkpoint_source(cwd)
    config = ResurrectConfig.load(cwd)
    client = DatabricksClient(config.databricks_host, config.databricks_token, config.databricks_warehouse_id)
    resolution: dict[str, object] = {"resolution": "", "commit": None, "confidence": "heuristic"}
    manifest_path: Path | None = None
    token_counter = {"value": 0}

    def add_tokens(chunk: str) -> None:
        token_counter["value"] += _estimate_tokens([chunk])

    stream_thread = threading.Thread(target=_stream_output, args=(process, add_tokens), daemon=True)
    stream_thread.start()

    try:
        while True:
            telemetry = parse_telemetry(checkpoint_source if checkpoint_source.exists() else _default_checkpoint_dir(cwd))
            current_signature = telemetry.error_signature.strip()
            if current_signature and not telemetry.status.is_complete:
                if current_signature == last_signature:
                    failures += 1
                else:
                    failures = 1
                last_signature = current_signature
            else:
                failures = 0
                last_signature = ""

            if failures >= max_failures:
                _terminate_process(process)
                resolution = client.fetch_resolution(telemetry.error_signature, telemetry.module_names[0] if telemetry.module_names else None)
                manifest_dir = cwd / ".resurrect"
                manifest_dir.mkdir(parents=True, exist_ok=True)
                manifest_path = write_handoff_manifest(manifest_dir / "handoff_manifest.json", telemetry, verified_match=bool(resolution.get("commit")))
                render_breaker_trip_panel(
                    tokens_intercepted=token_counter["value"],
                    estimated_dollars_saved=round(token_counter["value"] * 0.00002, 4),
                    sanitized_signature=telemetry.error_signature,
                    context_label="[COMPLETE CONTEXT]" if telemetry.status.is_complete else "[PARTIAL / REDACTED CONTEXT]",
                    resolution=resolution,
                )
                return WatchResult(
                    ok=False,
                    failures=failures,
                    tokens_intercepted=token_counter["value"],
                    telemetry=telemetry,
                    resolution=resolution,
                    manifest_path=manifest_path,
                    status_line="breaker-tripped",
                )

            if process.poll() is not None:
                break

            time.sleep(poll_interval)
    finally:
        _terminate_process(process)

    return WatchResult(
        ok=process.returncode == 0,
        failures=failures,
        tokens_intercepted=token_counter["value"],
        telemetry=telemetry,
        resolution=resolution,
        manifest_path=manifest_path,
        status_line="process-exited",
    )
