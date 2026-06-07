import os
from pathlib import Path

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


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


def test_init_writes_config_yaml(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert Path("config.yaml").exists()


def test_init_output_is_valid_yaml(tmp_path):
    import yaml
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        content = Path("config.yaml").read_text()
        parsed = yaml.safe_load(content)
        assert "models" in parsed


def test_init_refuses_to_overwrite_existing(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("config.yaml").write_text("existing content")
        result = runner.invoke(app, ["init"])
        assert result.exit_code != 0
        # Existing file must not have been overwritten
        assert Path("config.yaml").read_text() == "existing content"


def test_init_force_overwrites_existing(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("config.yaml").write_text("old content")
        result = runner.invoke(app, ["init", "--force"])
        assert result.exit_code == 0
        assert Path("config.yaml").read_text() != "old content"
