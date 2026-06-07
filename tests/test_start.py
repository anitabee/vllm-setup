from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from vllm_cli.adapters.ports import PortOccupant
from vllm_cli.cli import app
from vllm_cli.errors import DockerUnavailableError, OperationError
from vllm_cli.models import ResolvedModel, RuntimeContainer

runner = CliRunner()

_MINIMAL_CONFIG = """\
defaults:
  models_volume: /data/models
  gpus: all

models:
  laguna-xs:
    model: poolside/laguna-xs
    port: 8001
  qwen:
    model: Qwen/Qwen2.5-Coder-32B-Instruct
    port: 8002
    tensor_parallel_size: 2
    max_model_len: 4096
    extra_args: ["--enforce-eager"]
"""

_FAKE_RC = RuntimeContainer(
    name="vllm-laguna-xs",
    model="laguna-xs",
    port=8001,
    bind_address="127.0.0.1",
    status="running",
    base_url="http://127.0.0.1:8001/v1",
    readiness="loading",
)


@pytest.fixture()
def config_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(_MINIMAL_CONFIG)
    return p


# ---------------------------------------------------------------------------
# start — happy path
# ---------------------------------------------------------------------------


def test_start_calls_docker_with_resolved_model(config_file):
    with (
        patch("vllm_cli.cli._ports.find_port_occupant", return_value=None),
        patch("vllm_cli.cli._docker.start_model", return_value=_FAKE_RC) as mock_start,
    ):
        result = runner.invoke(app, ["start", "laguna-xs", "--config", str(config_file)])

    assert result.exit_code == 0
    mock_start.assert_called_once()
    rm: ResolvedModel = mock_start.call_args[0][0]
    assert rm.name == "laguna-xs"
    assert rm.model == "poolside/laguna-xs"
    assert rm.port == 8001
    assert rm.models_volume == "/data/models"
    assert rm.gpus == "all"


def test_start_prints_base_url(config_file):
    with (
        patch("vllm_cli.cli._ports.find_port_occupant", return_value=None),
        patch("vllm_cli.cli._docker.start_model", return_value=_FAKE_RC),
    ):
        result = runner.invoke(app, ["start", "laguna-xs", "--config", str(config_file)])

    assert result.exit_code == 0
    assert "http://127.0.0.1:8001/v1" in result.output


def test_start_passes_tensor_parallel_and_extra_args(config_file):
    with (
        patch("vllm_cli.cli._ports.find_port_occupant", return_value=None),
        patch("vllm_cli.cli._docker.start_model", return_value=_FAKE_RC) as mock_start,
    ):
        runner.invoke(app, ["start", "qwen", "--config", str(config_file)])

    rm: ResolvedModel = mock_start.call_args[0][0]
    assert rm.tensor_parallel_size == 2
    assert rm.max_model_len == 4096
    assert "--enforce-eager" in rm.extra_args


# ---------------------------------------------------------------------------
# start — port collision
# ---------------------------------------------------------------------------


def test_start_port_managed_collision_exits_3(config_file):
    occupant = PortOccupant(managed_model="qwen", pid=None, process_name=None)
    with (
        patch("vllm_cli.cli._ports.find_port_occupant", return_value=occupant),
        patch("vllm_cli.cli._docker.start_model") as mock_start,
    ):
        result = runner.invoke(app, ["start", "laguna-xs", "--config", str(config_file)])

    assert result.exit_code == 3
    assert "managed model qwen" in result.output
    mock_start.assert_not_called()


def test_start_port_unmanaged_collision_exits_3(config_file):
    occupant = PortOccupant(managed_model=None, pid=1234, process_name="nginx")
    with (
        patch("vllm_cli.cli._ports.find_port_occupant", return_value=occupant),
        patch("vllm_cli.cli._docker.start_model") as mock_start,
    ):
        result = runner.invoke(app, ["start", "laguna-xs", "--config", str(config_file)])

    assert result.exit_code == 3
    assert "1234" in result.output
    assert "nginx" in result.output
    mock_start.assert_not_called()


# ---------------------------------------------------------------------------
# start — error exits
# ---------------------------------------------------------------------------


def test_start_unknown_name_exits_2(config_file):
    result = runner.invoke(app, ["start", "no-such-model", "--config", str(config_file)])
    assert result.exit_code == 2


def test_start_docker_unavailable_exits_4(config_file):
    with (
        patch("vllm_cli.cli._ports.find_port_occupant", return_value=None),
        patch("vllm_cli.cli._docker.start_model", side_effect=DockerUnavailableError("no daemon")),
    ):
        result = runner.invoke(app, ["start", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 4


def test_start_operation_error_exits_5(config_file):
    with (
        patch("vllm_cli.cli._ports.find_port_occupant", return_value=None),
        patch("vllm_cli.cli._docker.start_model", side_effect=OperationError("container failed")),
    ):
        result = runner.invoke(app, ["start", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 5


# ---------------------------------------------------------------------------
# restart — composition
# ---------------------------------------------------------------------------


def test_restart_stops_then_starts(config_file):
    call_order: list[str] = []

    def fake_stop(name: str) -> bool:
        call_order.append(f"stop:{name}")
        return True

    def fake_start(rm: ResolvedModel) -> RuntimeContainer:
        call_order.append(f"start:{rm.name}")
        return _FAKE_RC

    with (
        patch("vllm_cli.cli._docker.stop_model", side_effect=fake_stop),
        patch("vllm_cli.cli._ports.find_port_occupant", return_value=None),
        patch("vllm_cli.cli._docker.start_model", side_effect=fake_start),
    ):
        result = runner.invoke(app, ["restart", "laguna-xs", "--config", str(config_file)])

    assert result.exit_code == 0
    assert call_order == ["stop:laguna-xs", "start:laguna-xs"]


def test_restart_unknown_name_exits_2(config_file):
    result = runner.invoke(app, ["restart", "no-such-model", "--config", str(config_file)])
    assert result.exit_code == 2


def test_restart_docker_unavailable_exits_4(config_file):
    with patch("vllm_cli.cli._docker.stop_model", side_effect=DockerUnavailableError("no daemon")):
        result = runner.invoke(app, ["restart", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 4
