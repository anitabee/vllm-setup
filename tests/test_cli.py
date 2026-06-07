import pytest
from typer.testing import CliRunner

from vllm_cli import __version__
from vllm_cli.cli import app

runner = CliRunner()


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    output = result.output.lower()
    assert "usage" in output or "commands" in output or "help" in output


def test_help_long_flag():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "vllm-cli" in result.output.lower() or "usage" in result.output.lower()


def test_help_short_flag():
    result = runner.invoke(app, ["-h"])
    assert result.exit_code == 0


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_command_shows_top_level_help():
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0
    # Should show something about the CLI, not an empty page
    assert len(result.output.strip()) > 0


def test_help_config_contains_all_fields():
    result = runner.invoke(app, ["help", "config"])
    assert result.exit_code == 0
    for field_name in ("image", "gpus", "bind_address", "models_volume", "dtype",
                        "extra_args", "model", "port", "served_name",
                        "tensor_parallel_size", "max_model_len"):
        assert field_name in result.output, f"Field '{field_name}' missing from help config output"


def test_no_color_flag_accepted():
    result = runner.invoke(app, ["--no-color", "help", "config"])
    assert result.exit_code == 0


def test_no_input_flag_accepted():
    result = runner.invoke(app, ["--no-input", "help", "config"])
    assert result.exit_code == 0
