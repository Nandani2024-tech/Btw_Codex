from __future__ import annotations

from pathlib import Path
import shlex

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from resurrect.config import ResurrectConfig
from resurrect.core.databricks_client import DatabricksClient
from resurrect.core.entire_bridge import CommandResult, check_entire_status, setup_entire
from resurrect.handoff import build_handoff_manifest, write_handoff_manifest
from resurrect.parser import ParsedTelemetry, parse_telemetry
from resurrect.ui.console import StatusItem, render_status_board
from resurrect.watcher import watch_agent


app = typer.Typer(help="Agent Resurrect command-line interface.")
console = Console()


@app.callback(invoke_without_command=True)
def main() -> None:
    """Entry point for the resurrect CLI."""
    return None


@app.command()
def init(
    agent: str = "codex",
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug details."),
    cwd: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    result = setup_entire(agent=agent, cwd=cwd)
    config = ResurrectConfig().save(cwd)
    if verbose or not result.ok:
        _render_debug("entire enable", result, cwd)
    if result.ok:
        typer.echo(f"Created {config}")
        typer.echo("Populate these fields in .resurrect/config.json:")
        typer.echo("  - databricks_host")
        typer.echo("  - databricks_token")
        typer.echo("  - databricks_warehouse_id")
    else:
        raise typer.Exit(code=1)


@app.command()
def doctor(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug details."),
    cwd: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    config = ResurrectConfig.load(cwd)
    items: list[StatusItem] = []

    missing = config.missing_fields()
    items.append(StatusItem("Config", not missing, "All required values loaded." if not missing else f"Missing: {', '.join(missing)}"))

    entire_status = check_entire_status(cwd)
    items.append(StatusItem("Entire", entire_status.ok, entire_status.stderr or entire_status.stdout))
    if verbose or not entire_status.ok:
        _render_debug("entire status", entire_status, cwd)

    client = DatabricksClient(config.databricks_host, config.databricks_token, config.databricks_warehouse_id)
    ping = client.ping_connection()
    items.append(StatusItem("Databricks ping", ping.ok, ping.error or (f"{ping.latency_ms:.1f} ms" if ping.latency_ms is not None else "")))

    table = client.verify_table_exists(config.delta_table_name)
    items.append(StatusItem("Delta table", table.ok, table.error or f"{config.delta_table_name} is queryable"))

    telemetry = parse_telemetry(cwd / "refs" / "entire" / "checkpoints")
    query_result = client.query_failure_traps(telemetry, config.delta_table_name)
    context_label = "[PARTIAL / REDACTED CONTEXT]" if not telemetry.status.is_complete else "[COMPLETE CONTEXT]"
    items.append(StatusItem("Failure traps", query_result.ok, query_result.error or telemetry.error_signature, context_label=context_label))

    render_status_board(items)
    manifest_dir = cwd / ".resurrect"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    write_handoff_manifest(manifest_dir / "handoff_manifest.json", telemetry, verified_match=query_result.ok and telemetry.status.is_complete)
    if not all(item.ok for item in items):
        raise typer.Exit(code=1)


@app.command("run")
def run(
    command_str: str,
    cwd: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    command = shlex.split(command_str)
    if not command:
        raise typer.Exit(code=2)
    typer.echo(f"Running: {command_str}")
    result = watch_agent(command)
    if not result.ok:
        raise typer.Exit(code=1)


@app.command("inspect-checkpoint")
def inspect_checkpoint(
    cwd: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    checkpoint_dir = cwd / "refs" / "entire" / "checkpoints"
    telemetry = parse_telemetry(checkpoint_dir)
    manifest = build_handoff_manifest(telemetry, verified_match=telemetry.status.is_complete)
    estimated_tokens = max(1, len(telemetry.error_signature) // 4) if telemetry.error_signature else 0
    table = StatusItem(
        "Latest checkpoint",
        telemetry.status.is_complete,
        f"tokens~={estimated_tokens} privacy={telemetry.privacy_provenance} source={telemetry.source_path or checkpoint_dir}",
        context_label=manifest.status_label,
    )
    render_status_board([table], title="Checkpoint Inspection")
    typer.echo(f"Error signature: {telemetry.error_signature or '<none>'}")
    typer.echo(f"Missing fields: {', '.join(telemetry.status.missing_fields) or '<none>'}")
    typer.echo(f"Confidence: {telemetry.status.confidence}")
    typer.echo(f"Privacy: {telemetry.privacy_provenance}")


def _render_debug(label: str, result: CommandResult, cwd: Path) -> None:
    body = Text()
    body.append(f"Running: {result.command}\n", style="dim")
    body.append(f"cwd: {cwd}\n", style="dim")
    body.append(f"returncode: {result.returncode}\n", style="dim")
    body.append("stdout:\n", style="bold")
    body.append(f"{result.stdout or '<empty>'}\n")
    body.append("stderr:\n", style="bold")
    body.append(f"{result.stderr or '<empty>'}")
    console.print(Panel(body, title=f"Debug: {label}", border_style="yellow"))
