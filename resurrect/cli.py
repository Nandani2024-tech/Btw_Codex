from __future__ import annotations

from pathlib import Path

import typer

from resurrect.config import ResurrectConfig
from resurrect.core.databricks_client import DatabricksClient, DiagnosticResult
from resurrect.core.entire_bridge import check_entire_status, setup_entire
from resurrect.ui.console import StatusItem, render_status_board


app = typer.Typer(help="Agent Resurrect command-line interface.")


@app.callback(invoke_without_command=True)
def main() -> None:
    """Entry point for the resurrect CLI."""
    return None


@app.command()
def init(agent: str = "codex", cwd: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False, dir_okay=True, resolve_path=True)) -> None:
    result = setup_entire(agent=agent, cwd=cwd)
    config = ResurrectConfig().save(cwd)
    if result.ok:
        typer.echo(f"Initialized Entire hooks and created {config}")
    else:
        raise typer.Exit(code=1)


@app.command()
def doctor(cwd: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False, dir_okay=True, resolve_path=True)) -> None:
    config = ResurrectConfig.load(cwd)
    items: list[StatusItem] = []

    missing = config.missing_fields()
    items.append(StatusItem("Config", not missing, "All required values loaded." if not missing else f"Missing: {', '.join(missing)}"))

    entire_status = check_entire_status(cwd)
    items.append(StatusItem("Entire", entire_status.ok, entire_status.stderr or entire_status.stdout))

    client = DatabricksClient(config.databricks_host, config.databricks_token, config.databricks_warehouse_id)
    ping = client.ping_connection()
    items.append(StatusItem("Databricks ping", ping.ok, ping.error or (f"{ping.latency_ms:.1f} ms" if ping.latency_ms is not None else "")))

    table = client.verify_table_exists(config.delta_table_name)
    items.append(StatusItem("Delta table", table.ok, table.error or f"{config.delta_table_name} is queryable"))

    render_status_board(items)
    if not all(item.ok for item in items):
        raise typer.Exit(code=1)
