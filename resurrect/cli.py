import typer


app = typer.Typer(help="Agent Resurrect command-line interface.")


@app.callback(invoke_without_command=True)
def main() -> None:
    """Entry point for the resurrect CLI."""
    return None

