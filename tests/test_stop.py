from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from vllm_cli.cli import app
from vllm_cli.errors import DockerUnavailableError, OperationError

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


# ---------------------------------------------------------------------------
# stop <name>
# ---------------------------------------------------------------------------


def test_stop_running_model_reports_stopped(config_file):
    with patch("vllm_cli.cli._docker.stop_model", return_value=True) as mock_stop:
        result = runner.invoke(app, ["stop", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "laguna-xs" in result.output
    mock_stop.assert_called_once_with("laguna-xs")


def test_stop_not_running_reports_noop(config_file):
    with patch("vllm_cli.cli._docker.stop_model", return_value=False):
        result = runner.invoke(app, ["stop", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "not running" in result.output


def test_stop_unknown_name_exits_2(config_file):
    result = runner.invoke(app, ["stop", "no-such-model", "--config", str(config_file)])
    assert result.exit_code == 2


def test_stop_docker_unavailable_exits_4(config_file):
    with patch("vllm_cli.cli._docker.stop_model", side_effect=DockerUnavailableError("no daemon")):
        result = runner.invoke(app, ["stop", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 4


def test_stop_operation_error_exits_5(config_file):
    with patch("vllm_cli.cli._docker.stop_model", side_effect=OperationError("kill failed")):
        result = runner.invoke(app, ["stop", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 5


# ---------------------------------------------------------------------------
# stop-all
# ---------------------------------------------------------------------------


def test_stop_all_reports_stopped_names():
    with patch("vllm_cli.cli._docker.stop_all", return_value=["laguna-xs", "qwen"]) as mock_stop:
        result = runner.invoke(app, ["stop-all"])
    assert result.exit_code == 0
    assert "laguna-xs" in result.output
    assert "qwen" in result.output
    mock_stop.assert_called_once_with(force=False)


def test_stop_all_force_passes_flag():
    with patch("vllm_cli.cli._docker.stop_all", return_value=["laguna-xs"]) as mock_stop:
        result = runner.invoke(app, ["stop-all", "--force"])
    assert result.exit_code == 0
    mock_stop.assert_called_once_with(force=True)


def test_stop_all_no_containers_reports_clearly():
    with patch("vllm_cli.cli._docker.stop_all", return_value=[]):
        result = runner.invoke(app, ["stop-all"])
    assert result.exit_code == 0
    assert "No managed containers" in result.output


def test_stop_all_docker_unavailable_exits_4():
    with patch("vllm_cli.cli._docker.stop_all", side_effect=DockerUnavailableError("no daemon")):
        result = runner.invoke(app, ["stop-all"])
    assert result.exit_code == 4


def test_stop_all_operation_error_exits_5():
    with patch("vllm_cli.cli._docker.stop_all", side_effect=OperationError("remove failed")):
        result = runner.invoke(app, ["stop-all"])
    assert result.exit_code == 5


def test_stop_all_label_filtering_is_adapter_responsibility():
    """stop-all must only operate on containers the adapter returns (managed-by label).
    The CLI passes no extra scope-widening args to the adapter."""
    with patch("vllm_cli.cli._docker.stop_all", return_value=[]) as mock_stop:
        runner.invoke(app, ["stop-all"])
    mock_stop.assert_called_once_with(force=False)


def test_stop_all_force_label_filtering_unchanged():
    """--force must not bypass label filtering — adapter is still the single choke-point."""
    with patch("vllm_cli.cli._docker.stop_all", return_value=[]) as mock_stop:
        runner.invoke(app, ["stop-all", "--force"])
    mock_stop.assert_called_once_with(force=True)
