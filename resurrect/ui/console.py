"""Rich console rendering for diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


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
