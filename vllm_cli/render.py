from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.table import Table

from vllm_cli.config import FIELD_REFERENCE


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
