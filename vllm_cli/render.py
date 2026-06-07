from __future__ import annotations

from rich.console import Console
from rich.table import Table

from vllm_cli.config import FIELD_REFERENCE
from vllm_cli.models import ResolvedModel, RuntimeContainer


def make_console(no_color: bool = False) -> Console:
    """Return a stdout Console. Color is disabled when --no-color is set;
    Rich handles TTY detection and NO_COLOR automatically."""
    if no_color:
        return Console(color_system=None)
    return Console()


def make_error_console() -> Console:
    return Console(stderr=True)


def print_field_reference(console: Console) -> None:
    table = Table(title="Configuration Field Reference", show_lines=True, expand=False)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Scope", style="dim")
    table.add_column("Meaning")
    table.add_column("Values / Default", style="green")

    for f in FIELD_REFERENCE:
        table.add_row(f.name, f.scope, f.meaning, f.values_default)

    console.print(table)


def list_models(
    console: Console,
    models: list[ResolvedModel],
    downloaded: set[str],
    running: set[str],
) -> None:
    """Print the registry view: each model with download label and flush-right RUNNING."""
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0), expand=True)
    table.add_column("name", style="bold")
    table.add_column("download")
    table.add_column("running", justify="right")

    for m in models:
        dl_label = "Downloaded" if m.model in downloaded else "not downloaded"
        run_label = "RUNNING" if m.name in running else ""
        table.add_row(m.name, dl_label, run_label)

    console.print(table)


def print_ps(console: Console, containers: list[RuntimeContainer]) -> None:
    """Print the ps runtime view: live managed containers with readiness."""
    if not containers:
        console.print("No managed containers running")
        return

    table = Table(show_header=True, box=None, padding=(0, 2, 0, 0))
    table.add_column("NAME", style="bold")
    table.add_column("MODEL")
    table.add_column("PORT")
    table.add_column("STATUS")
    table.add_column("BASE URL")
    table.add_column("READINESS")

    for c in containers:
        readiness_style = "green" if c.readiness == "ready" else "yellow"
        table.add_row(
            c.name,
            c.model,
            str(c.port),
            c.status,
            c.base_url,
            f"[{readiness_style}]{c.readiness}[/{readiness_style}]",
        )

    console.print(table)
