"""Helpers for Entire CLI integration."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CommandResult:
    ok: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None


def _run(command: list[str], cwd: Path | str | None = None) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        return CommandResult(
            ok=completed.returncode == 0,
            command=" ".join(command),
            stdout=stdout,
            stderr=stderr,
            returncode=completed.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            ok=False,
            command=" ".join(command),
            stdout=(exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            stderr=f"Command timed out after 15 seconds while running: {' '.join(command)}",
            returncode=None,
        )
    except FileNotFoundError as exc:
        return CommandResult(
            ok=False,
            command=" ".join(command),
            stderr=f"Command not found: {command[0]}. Install it and ensure it is on PATH. Details: {exc}",
            returncode=None,
        )
    except Exception as exc:
        return CommandResult(
            ok=False,
            command=" ".join(command),
            stderr=f"Failed to run {' '.join(command)} in {cwd}: {exc}",
            returncode=None,
        )


def setup_entire(agent: str = "codex", cwd: Path | str = Path.cwd()) -> CommandResult:
    git_dir = Path(cwd) / ".git"
    if not git_dir.exists():
        return CommandResult(ok=False, command="git rev-parse --is-inside-work-tree", stderr="Git repository not initialized.")

    enable = _run(["entire", "enable", "--force"], cwd=cwd)
    if not enable.ok:
        return enable

    hooks = _run(["entire", "hooks", "configure", "--agent", agent], cwd=cwd)
    if not hooks.ok:
        return hooks

    return CommandResult(
        ok=True,
        command=f"entire enable --force && entire hooks configure --agent {agent}",
        stdout="\n".join(part for part in [enable.stdout, hooks.stdout] if part),
        stderr="\n".join(part for part in [enable.stderr, hooks.stderr] if part),
        returncode=0,
    )


def check_entire_status(cwd: Path | str = Path.cwd()) -> CommandResult:
    status = _run(["entire", "status"], cwd=cwd)
    text = f"{status.stdout}\n{status.stderr}".lower()
    if status.returncode == 0 and ("enabled" in text or "checkpoints active" in text):
        first_line = (status.stdout or "").splitlines()[0] if (status.stdout or "").splitlines() else ""
        detail = f"Entire active ({first_line})" if first_line else "Entire active"
        return CommandResult(
            ok=True,
            command=status.command,
            stdout=status.stdout,
            stderr=detail,
            returncode=status.returncode,
        )
    if not status.ok:
        return status
    if "checkpoint" not in text or ("active" not in text and "enabled" not in text):
        return CommandResult(
            ok=False,
            command=status.command,
            stdout=status.stdout,
            stderr=status.stderr or "Entire is not enabled on this repository.",
            returncode=status.returncode,
        )
    return status
