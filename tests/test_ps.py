from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from rich.console import Console
from typer.testing import CliRunner

from vllm_cli.cli import app
from vllm_cli.errors import DockerUnavailableError
from vllm_cli.models import RuntimeContainer
from vllm_cli import render as _render

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _container(
    name: str = "vllm-laguna",
    model: str = "poolside/laguna-xs",
    port: int = 8001,
    bind_address: str = "127.0.0.1",
    status: str = "running",
    readiness: str = "loading",
) -> RuntimeContainer:
    return RuntimeContainer(
        name=name,
        model=model,
        port=port,
        bind_address=bind_address,
        status=status,
        base_url=f"http://{bind_address}:{port}/v1",
        readiness=readiness,
    )


def _render_ps(containers: list[RuntimeContainer]) -> str:
    buf = StringIO()
    console = Console(file=buf, color_system=None, width=120)
    _render.print_ps(console, containers)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Render unit tests
# ---------------------------------------------------------------------------


def test_render_ps_shows_name_and_model():
    out = _render_ps([_container(name="vllm-laguna", model="poolside/laguna-xs")])
    assert "vllm-laguna" in out
    assert "poolside/laguna-xs" in out


def test_render_ps_shows_port_and_base_url():
    out = _render_ps([_container(port=8001, bind_address="127.0.0.1")])
    assert "8001" in out
    assert "http://127.0.0.1:8001/v1" in out


def test_render_ps_shows_loading():
    out = _render_ps([_container(readiness="loading")])
    assert "loading" in out


def test_render_ps_shows_ready():
    out = _render_ps([_container(readiness="ready")])
    assert "ready" in out


def test_render_ps_shows_status():
    out = _render_ps([_container(status="running")])
    assert "running" in out


def test_render_ps_multiple_containers():
    containers = [
        _container(name="vllm-a", port=8001, readiness="ready"),
        _container(name="vllm-b", port=8002, readiness="loading"),
    ]
    out = _render_ps(containers)
    assert "vllm-a" in out
    assert "vllm-b" in out
    assert "ready" in out
    assert "loading" in out


def test_render_ps_empty_state():
    out = _render_ps([])
    assert "No managed containers running" in out


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def test_ps_empty_state_exit_0():
    with (
        patch("vllm_cli.cli._docker.list_runtime_containers", return_value=[]),
    ):
        result = runner.invoke(app, ["ps"])
    assert result.exit_code == 0
    assert "No managed containers running" in result.output


def test_ps_shows_loading_container():
    c = _container(readiness="loading")
    with (
        patch("vllm_cli.cli._docker.list_runtime_containers", return_value=[c]),
        patch("vllm_cli.cli._health.check_readiness", return_value="loading"),
    ):
        result = runner.invoke(app, ["ps"])
    assert result.exit_code == 0
    assert "loading" in result.output
    assert "vllm-laguna" in result.output


def test_ps_shows_ready_container():
    c = _container(readiness="loading")
    with (
        patch("vllm_cli.cli._docker.list_runtime_containers", return_value=[c]),
        patch("vllm_cli.cli._health.check_readiness", return_value="ready"),
    ):
        result = runner.invoke(app, ["ps"])
    assert result.exit_code == 0
    assert "ready" in result.output


def test_ps_health_called_with_base_url():
    c = _container(port=8001, bind_address="127.0.0.1")
    with (
        patch("vllm_cli.cli._docker.list_runtime_containers", return_value=[c]),
        patch("vllm_cli.cli._health.check_readiness", return_value="loading") as mock_health,
    ):
        runner.invoke(app, ["ps"])
    mock_health.assert_called_once_with("http://127.0.0.1:8001/v1")


def test_ps_exit_4_when_docker_unavailable():
    with patch(
        "vllm_cli.cli._docker.list_runtime_containers",
        side_effect=DockerUnavailableError("daemon not running"),
    ):
        result = runner.invoke(app, ["ps"])
    assert result.exit_code == 4


def test_ps_only_shows_running_containers():
    """Non-running containers never appear — docker_adapter filters them."""
    c = _container(name="vllm-live", status="running", readiness="ready")
    with (
        patch("vllm_cli.cli._docker.list_runtime_containers", return_value=[c]),
        patch("vllm_cli.cli._health.check_readiness", return_value="ready"),
    ):
        result = runner.invoke(app, ["ps"])
    assert "vllm-live" in result.output
