"""Rich console rendering for diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass(slots=True)
class StatusItem:
    name: str
    ok: bool
    detail: str = ""
    context_label: str = ""


def render_status_board(items: list[StatusItem], title: str = "Resurrect Doctor") -> Console:
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    for item in items:
        status = "[green]PASS[/green]" if item.ok else "[red]FAIL[/red]"
        check = "[green]✓[/green]" if item.ok else "[yellow]![/yellow]"
        detail = item.detail or ""
        if item.context_label:
            detail = f"{item.context_label} {detail}".strip()
        table.add_row(f"{check} {item.name}", status, detail)
    console.print(Panel(table, title=title, border_style="blue"))
    return console


def render_breaker_trip_panel(
    *,
    tokens_intercepted: int,
    estimated_dollars_saved: float,
    sanitized_signature: str,
    context_label: str,
    resolution: dict[str, object],
) -> Console:
    console = Console()
    header = Text("🚨 [CIRCUIT BREAKER TRIPPED]: Infinite Repair Loop Detected!", style="bold red")
    body = Table(show_header=False, box=None, pad_edge=False)
    body.add_column("Field", style="bold")
    body.add_column("Value")
    body.add_row("Tokens intercepted", str(tokens_intercepted))
    body.add_row("Estimated dollars saved", f"${estimated_dollars_saved:.4f}")
    body.add_row("Sanitized signature", sanitized_signature or "<unknown>")
    body.add_row("Context", context_label)
    console.print(Panel(body, title=header, border_style="red"))

    resolution_body = Table(show_header=False, box=None, pad_edge=False)
    resolution_body.add_column("Field", style="bold")
    resolution_body.add_column("Value")
    resolution_body.add_row("Databricks resolution", str(resolution.get("resolution") or "<none>"))
    resolution_body.add_row("Source commit", str(resolution.get("commit") or "<unknown>"))
    resolution_body.add_row("Confidence", str(resolution.get("confidence") or "<unknown>"))
    console.print(Panel(resolution_body, title="Resolution", border_style="green"))
    return console
