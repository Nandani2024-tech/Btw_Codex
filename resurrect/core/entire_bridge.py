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
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        ok=completed.returncode == 0,
        command=" ".join(command),
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        returncode=completed.returncode,
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
    if not status.ok:
        return status
    text = f"{status.stdout}\n{status.stderr}".lower()
    if "checkpoint" not in text or ("active" not in text and "enabled" not in text):
        return CommandResult(
            ok=False,
            command=status.command,
            stdout=status.stdout,
            stderr="Entire checkpoints are not reported as active.",
            returncode=status.returncode,
        )
    return status
