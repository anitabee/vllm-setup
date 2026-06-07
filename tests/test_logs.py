from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from vllm_cli.cli import app
from vllm_cli.errors import DockerUnavailableError, UnknownContainerError

runner = CliRunner()

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


def test_logs_streams_output_for_correct_container(config_file):
    log_lines = [b"Loading model...\n", b"Model ready.\n"]
    with patch("vllm_cli.cli._docker.stream_container_logs", side_effect=lambda n: None) as mock_logs:
        result = runner.invoke(app, ["logs", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 0
    mock_logs.assert_called_once_with("laguna-xs")


def test_logs_passes_correct_name_to_adapter(config_file):
    with patch("vllm_cli.cli._docker.stream_container_logs") as mock_logs:
        runner.invoke(app, ["logs", "qwen", "--config", str(config_file)])
    mock_logs.assert_called_once_with("qwen")


def test_logs_unknown_model_name_exits_2(config_file):
    result = runner.invoke(app, ["logs", "no-such-model", "--config", str(config_file)])
    assert result.exit_code == 2


def test_logs_no_running_container_reports_clearly(config_file):
    with patch(
        "vllm_cli.cli._docker.stream_container_logs",
        side_effect=UnknownContainerError("laguna-xs"),
    ):
        result = runner.invoke(app, ["logs", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "laguna-xs" in result.output


def test_logs_docker_unavailable_exits_4(config_file):
    with patch(
        "vllm_cli.cli._docker.stream_container_logs",
        side_effect=DockerUnavailableError("no daemon"),
    ):
        result = runner.invoke(app, ["logs", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 4
