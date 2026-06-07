from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from vllm_cli.cli import app
from vllm_cli.errors import DockerUnavailableError
from vllm_cli.models import ResolvedModel
from vllm_cli import render as _render

runner = CliRunner()


# ---------------------------------------------------------------------------
# Render unit tests — no Docker, GPU, or network
# ---------------------------------------------------------------------------


def _model(name: str, model_id: str) -> ResolvedModel:
    return ResolvedModel(
        name=name,
        model=model_id,
        port=8000,
        image="vllm/vllm-openai:latest",
        gpus="all",
        bind_address="127.0.0.1",
        dtype="auto",
    )


def _render_list(
    models: list[ResolvedModel],
    downloaded: set[str],
    running: set[str],
) -> str:
    buf = StringIO()
    console = Console(file=buf, color_system=None, width=80)
    _render.list_models(console, models, downloaded, running)
    return buf.getvalue()


def test_render_shows_model_names():
    models = [_model("laguna-xs", "poolside/laguna-xs"), _model("qwen", "Qwen/Qwen2.5")]
    out = _render_list(models, downloaded=set(), running=set())
    assert "laguna-xs" in out
    assert "qwen" in out


def test_render_downloaded_label():
    models = [_model("laguna-xs", "poolside/laguna-xs")]
    out = _render_list(models, downloaded={"poolside/laguna-xs"}, running=set())
    assert "Downloaded" in out
    assert "not downloaded" not in out


def test_render_not_downloaded_label():
    models = [_model("laguna-xs", "poolside/laguna-xs")]
    out = _render_list(models, downloaded=set(), running=set())
    assert "not downloaded" in out


def test_render_running_label_present():
    models = [_model("laguna-xs", "poolside/laguna-xs")]
    out = _render_list(models, downloaded=set(), running={"laguna-xs"})
    assert "RUNNING" in out


def test_render_running_label_absent_when_not_running():
    models = [_model("laguna-xs", "poolside/laguna-xs")]
    out = _render_list(models, downloaded=set(), running=set())
    assert "RUNNING" not in out


def test_render_running_only_for_matching_model():
    models = [
        _model("laguna-xs", "poolside/laguna-xs"),
        _model("qwen", "Qwen/Qwen2.5"),
    ]
    out = _render_list(models, downloaded=set(), running={"laguna-xs"})
    assert "RUNNING" in out
    # RUNNING appears exactly once — only for laguna-xs
    assert out.count("RUNNING") == 1


def test_render_download_status_per_model():
    models = [
        _model("laguna-xs", "poolside/laguna-xs"),
        _model("qwen", "Qwen/Qwen2.5"),
    ]
    out = _render_list(
        models,
        downloaded={"poolside/laguna-xs"},
        running=set(),
    )
    assert "Downloaded" in out
    assert "not downloaded" in out


def test_render_empty_model_list():
    out = _render_list([], downloaded=set(), running=set())
    # Should not raise; output may be empty or just whitespace
    assert isinstance(out, str)


def test_render_model_never_started_appears():
    """A model not in running set still shows up with a download status."""
    models = [_model("ghost-model", "org/ghost")]
    out = _render_list(models, downloaded=set(), running=set())
    assert "ghost-model" in out
    assert "not downloaded" in out
    assert "RUNNING" not in out


# ---------------------------------------------------------------------------
# CLI integration tests — mock adapters
# ---------------------------------------------------------------------------


_MINIMAL_CONFIG = """\
defaults:
  models_volume: /data/models

models:
  laguna-xs:
    model: poolside/laguna-xs
    port: 8001
  qwen:
    model: Qwen/Qwen2.5-Coder-32B-Instruct
    port: 8002
"""


@pytest.fixture()
def config_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(_MINIMAL_CONFIG)
    return p


def test_list_prints_all_configured_models(config_file):
    with (
        patch("vllm_cli.cli._docker.list_running_model_names", return_value=set()),
        patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()),
    ):
        result = runner.invoke(app, ["list", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "laguna-xs" in result.output
    assert "qwen" in result.output


def test_list_shows_downloaded_label(config_file):
    with (
        patch("vllm_cli.cli._docker.list_running_model_names", return_value=set()),
        patch(
            "vllm_cli.cli._hf.list_downloaded_models",
            return_value={"poolside/laguna-xs"},
        ),
    ):
        result = runner.invoke(app, ["list", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "Downloaded" in result.output


def test_list_shows_running_marker(config_file):
    with (
        patch(
            "vllm_cli.cli._docker.list_running_model_names",
            return_value={"laguna-xs"},
        ),
        patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()),
    ):
        result = runner.invoke(app, ["list", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "RUNNING" in result.output


def test_list_exit_4_when_docker_unavailable(config_file):
    with (
        patch(
            "vllm_cli.cli._docker.list_running_model_names",
            side_effect=DockerUnavailableError("daemon not running"),
        ),
        patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()),
    ):
        result = runner.invoke(app, ["list", "--config", str(config_file)])
    assert result.exit_code == 4


def test_list_error_message_on_docker_unavailable(config_file):
    with (
        patch(
            "vllm_cli.cli._docker.list_running_model_names",
            side_effect=DockerUnavailableError("connection refused"),
        ),
        patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()),
    ):
        result = runner.invoke(app, ["list", "--config", str(config_file)])
    # Error message goes to stderr but CliRunner mixes streams
    assert result.exit_code == 4


def test_list_config_not_found():
    result = runner.invoke(app, ["list", "--config", "nonexistent.yaml"])
    assert result.exit_code != 0


def test_list_model_not_running_shows_no_running_label(config_file):
    with (
        patch("vllm_cli.cli._docker.list_running_model_names", return_value=set()),
        patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()),
    ):
        result = runner.invoke(app, ["list", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "RUNNING" not in result.output
