from __future__ import annotations

from typing import Optional

import typer

from vllm_cli import __version__
from vllm_cli import logging_setup as _logging_setup
from vllm_cli import render as _render

app = typer.Typer(
    name="vllm-cli",
    help="Manage local vLLM Docker containers.",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

help_app = typer.Typer(help="Show built-in documentation topics.")
app.add_typer(help_app, name="help")

# Module-level state set by the main callback before any command runs.
_state: dict[str, object] = {"no_color": False, "no_input": False}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"vllm-cli {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    no_color: bool = typer.Option(False, "--no-color", help="Disable color output."),
    no_input: bool = typer.Option(False, "--no-input", help="Disable interactive prompts."),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    _logging_setup.setup()
    _state["no_color"] = no_color
    _state["no_input"] = no_input
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@help_app.callback(invoke_without_command=True)
def _help_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        # `vllm-cli help` with no topic shows the top-level command surface.
        typer.echo(ctx.parent.get_help())
        raise typer.Exit(0)


@help_app.command("config")
def help_config() -> None:
    """Print the full configuration field reference (all fields, scopes, and defaults)."""
    console = _render.make_console(bool(_state["no_color"]))
    _render.print_field_reference(console)
