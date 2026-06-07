from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from vllm_cli.cli import app
from vllm_cli.errors import DownloadError

runner = CliRunner()

_CONFIG = """\
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

_CONFIG_NO_VOLUME = """\
models:
  my-model:
    model: org/model
    port: 8001
"""


@pytest.fixture()
def config_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(_CONFIG)
    return p


@pytest.fixture()
def config_no_volume(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(_CONFIG_NO_VOLUME)
    return p


# ---------------------------------------------------------------------------
# No-arg: list not-yet-downloaded models
# ---------------------------------------------------------------------------


def test_no_arg_lists_not_downloaded(config_file):
    with patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()):
        result = runner.invoke(app, ["download", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "laguna-xs" in result.output
    assert "qwen" in result.output


def test_no_arg_omits_already_downloaded(config_file):
    with patch(
        "vllm_cli.cli._hf.list_downloaded_models",
        return_value={"poolside/laguna-xs"},
    ):
        result = runner.invoke(app, ["download", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "laguna-xs" not in result.output
    assert "qwen" in result.output


def test_no_arg_all_downloaded_shows_message(config_file):
    with patch(
        "vllm_cli.cli._hf.list_downloaded_models",
        return_value={"poolside/laguna-xs", "Qwen/Qwen2.5-Coder-32B-Instruct"},
    ):
        result = runner.invoke(app, ["download", "--config", str(config_file)])
    assert result.exit_code == 0
    assert "already downloaded" in result.output.lower()


# ---------------------------------------------------------------------------
# Named download
# ---------------------------------------------------------------------------


def test_named_download_calls_hf_adapter(config_file):
    with (
        patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()),
        patch("vllm_cli.cli._hf.download_model") as mock_dl,
    ):
        result = runner.invoke(app, ["download", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 0
    mock_dl.assert_called_once_with(repo_id="poolside/laguna-xs", cache_dir="/data/models")


def test_named_download_unknown_name_exits_2(config_file):
    with patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()):
        result = runner.invoke(app, ["download", "no-such-model", "--config", str(config_file)])
    assert result.exit_code == 2


def test_named_download_failure_exits_6(config_file):
    with (
        patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()),
        patch(
            "vllm_cli.cli._hf.download_model",
            side_effect=DownloadError("network error"),
        ),
    ):
        result = runner.invoke(app, ["download", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 6


def test_named_download_failure_message_mentions_rerunnable(config_file):
    with (
        patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()),
        patch(
            "vllm_cli.cli._hf.download_model",
            side_effect=DownloadError("timeout"),
        ),
    ):
        result = runner.invoke(app, ["download", "laguna-xs", "--config", str(config_file)])
    assert result.exit_code == 6
    assert "re-runnable" in result.output


def test_named_download_no_volume_exits_2(config_no_volume):
    with patch("vllm_cli.cli._hf.list_downloaded_models", return_value=set()):
        result = runner.invoke(app, ["download", "my-model", "--config", str(config_no_volume)])
    assert result.exit_code == 2
