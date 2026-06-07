from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from vllm_cli import __version__
from vllm_cli import logging_setup as _logging_setup
from vllm_cli import render as _render
from vllm_cli.adapters import docker_adapter as _docker
from vllm_cli.adapters import hf_adapter as _hf
from vllm_cli.config import generate_init_yaml, load_config, resolve_all
from vllm_cli.errors import DockerUnavailableError, VllmCliError, exit_code_for

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


@app.command("list")
def list_cmd(
    config_path: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml."),
) -> None:
    """List configured models with download status and running state."""
    console = _render.make_console(bool(_state["no_color"]))
    err_console = _render.make_error_console()
    try:
        config = load_config(config_path)
        resolved = list(resolve_all(config).values())

        running = _docker.list_running_model_names()

        unique_volumes = {rm.models_volume for rm in resolved}
        downloaded: set[str] = set()
        for vol in unique_volumes:
            downloaded |= _hf.list_downloaded_models(vol)

        _render.list_models(console, resolved, downloaded, running)
    except DockerUnavailableError as exc:
        err_console.print(f"Error: Docker daemon is unreachable: {exc}")
        raise typer.Exit(4)
    except VllmCliError as exc:
        err_console.print(f"Error: {exc}")
        raise typer.Exit(exit_code_for(exc))


@app.command("init")
def init(
    force: bool = typer.Option(False, "--force", help="Overwrite an existing config.yaml."),
) -> None:
    """Write a starter config.yaml in the current directory."""
    path = Path("config.yaml")
    if path.exists() and not force:
        typer.echo(f"Error: {path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(1)
    path.write_text(generate_init_yaml())
    typer.echo(f"Written: {path}")
