from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from vllm_cli.config import (
    FIELD_REFERENCE,
    Config,
    Defaults,
    ModelEntry,
    generate_init_yaml,
    load_config,
    lookup_model,
    resolve_all,
    resolve_model,
)
from vllm_cli.errors import ConfigError, UnknownModelError


# ---------------------------------------------------------------------------
# FIELD_REFERENCE (from task 01, kept here)
# ---------------------------------------------------------------------------


def test_all_required_fields_present():
    names = {f.name for f in FIELD_REFERENCE}
    required = {"image", "gpus", "bind_address", "models_volume", "dtype", "extra_args",
                "model", "port", "served_name", "tensor_parallel_size", "max_model_len"}
    assert required == names


def test_per_model_required_fields_marked():
    scopes = {f.name: f.scope for f in FIELD_REFERENCE}
    assert "required" in scopes["model"]
    assert "required" in scopes["port"]


def test_field_reference_non_empty_descriptions():
    for f in FIELD_REFERENCE:
        assert f.meaning.strip(), f"{f.name} has empty meaning"
        assert f.values_default.strip(), f"{f.name} has empty values_default"


# ---------------------------------------------------------------------------
# Pydantic models — unit tests (no I/O)
# ---------------------------------------------------------------------------


def _make_config(raw: dict) -> Config:
    return Config.model_validate(raw)


def test_minimal_valid_config():
    cfg = _make_config({
        "models": {
            "llama": {"model": "meta-llama/Llama-3-8B", "port": 8000}
        }
    })
    assert cfg.models["llama"].model == "meta-llama/Llama-3-8B"
    assert cfg.models["llama"].port == 8000


def test_defaults_applied_when_not_specified():
    cfg = _make_config({
        "models": {"m": {"model": "x/y", "port": 8001}}
    })
    assert cfg.defaults.image == "vllm/vllm-openai:latest"
    assert cfg.defaults.gpus == "all"
    assert cfg.defaults.bind_address == "127.0.0.1"
    assert cfg.defaults.dtype == "auto"
    assert cfg.defaults.extra_args == []
    assert cfg.defaults.models_volume is None


def test_explicit_defaults_override_builtin_defaults():
    cfg = _make_config({
        "defaults": {
            "image": "vllm/vllm-openai:v0.4.0",
            "gpus": "0",
            "bind_address": "0.0.0.0",
            "models_volume": "/mnt/models",
            "dtype": "float16",
            "extra_args": ["--flag"],
        },
        "models": {"m": {"model": "x/y", "port": 8000}}
    })
    assert cfg.defaults.image == "vllm/vllm-openai:v0.4.0"
    assert cfg.defaults.gpus == "0"
    assert cfg.defaults.bind_address == "0.0.0.0"
    assert cfg.defaults.models_volume == "/mnt/models"
    assert cfg.defaults.dtype == "float16"
    assert cfg.defaults.extra_args == ["--flag"]


# ---------------------------------------------------------------------------
# resolve_model — defaults/override merge
# ---------------------------------------------------------------------------


def test_resolve_uses_defaults_when_no_override():
    defaults = Defaults(
        image="vllm/vllm-openai:v0.4.0",
        gpus="0,1",
        bind_address="0.0.0.0",
        models_volume="/mnt/models",
        dtype="float16",
        extra_args=["--a"],
    )
    entry = ModelEntry(model="x/y", port=8000)
    resolved = resolve_model("my-model", entry, defaults)

    assert resolved.name == "my-model"
    assert resolved.model == "x/y"
    assert resolved.port == 8000
    assert resolved.image == "vllm/vllm-openai:v0.4.0"
    assert resolved.gpus == "0,1"
    assert resolved.bind_address == "0.0.0.0"
    assert resolved.models_volume == "/mnt/models"
    assert resolved.dtype == "float16"
    assert resolved.extra_args == ["--a"]


def test_resolve_model_overrides_win_over_defaults():
    defaults = Defaults(image="vllm/vllm-openai:latest", gpus="all", dtype="auto")
    entry = ModelEntry(
        model="x/y",
        port=8000,
        image="custom:tag",
        gpus="0",
        dtype="bfloat16",
        extra_args=["--custom"],
    )
    resolved = resolve_model("m", entry, defaults)

    assert resolved.image == "custom:tag"
    assert resolved.gpus == "0"
    assert resolved.dtype == "bfloat16"
    assert resolved.extra_args == ["--custom"]


def test_resolve_optional_fields_passthrough():
    defaults = Defaults()
    entry = ModelEntry(
        model="x/y",
        port=8000,
        served_name="my-alias",
        tensor_parallel_size=2,
        max_model_len=4096,
    )
    resolved = resolve_model("m", entry, defaults)

    assert resolved.served_name == "my-alias"
    assert resolved.tensor_parallel_size == 2
    assert resolved.max_model_len == 4096


def test_resolve_optional_fields_none_when_unset():
    defaults = Defaults()
    entry = ModelEntry(model="x/y", port=8000)
    resolved = resolve_model("m", entry, defaults)

    assert resolved.served_name is None
    assert resolved.tensor_parallel_size is None
    assert resolved.max_model_len is None
    assert resolved.models_volume is None


def test_resolve_all_returns_all_models():
    cfg = _make_config({
        "models": {
            "a": {"model": "x/a", "port": 8000},
            "b": {"model": "x/b", "port": 8001},
        }
    })
    resolved = resolve_all(cfg)
    assert set(resolved.keys()) == {"a", "b"}
    assert resolved["a"].port == 8000
    assert resolved["b"].port == 8001


# ---------------------------------------------------------------------------
# Validation — required fields
# ---------------------------------------------------------------------------


def test_missing_model_field_raises_config_error(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent("""\
        models:
          my-model:
            port: 8000
    """))
    with pytest.raises(ConfigError) as exc_info:
        load_config(p)
    assert str(p) in str(exc_info.value)
    assert "my-model" in str(exc_info.value) or "model" in str(exc_info.value)


def test_missing_port_field_raises_config_error(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent("""\
        models:
          my-model:
            model: x/y
    """))
    with pytest.raises(ConfigError) as exc_info:
        load_config(p)
    assert str(p) in str(exc_info.value)
    assert "my-model" in str(exc_info.value) or "port" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Validation — duplicate ports
# ---------------------------------------------------------------------------


def test_duplicate_port_raises_config_error():
    with pytest.raises(Exception) as exc_info:
        _make_config({
            "models": {
                "alpha": {"model": "x/a", "port": 8000},
                "beta": {"model": "x/b", "port": 8000},
            }
        })
    msg = str(exc_info.value)
    assert "alpha" in msg or "beta" in msg
    assert "8000" in msg


def test_duplicate_port_config_error_via_load(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent("""\
        models:
          alpha:
            model: x/a
            port: 8000
          beta:
            model: x/b
            port: 8000
    """))
    with pytest.raises(ConfigError) as exc_info:
        load_config(p)
    msg = str(exc_info.value)
    assert "alpha" in msg
    assert "beta" in msg
    assert "8000" in msg


def test_non_duplicate_ports_valid():
    cfg = _make_config({
        "models": {
            "alpha": {"model": "x/a", "port": 8000},
            "beta": {"model": "x/b", "port": 8001},
        }
    })
    assert len(cfg.models) == 2


# ---------------------------------------------------------------------------
# load_config — file-level errors
# ---------------------------------------------------------------------------


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nonexistent.yaml")


def test_load_config_empty_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("")
    with pytest.raises(ConfigError, match="empty"):
        load_config(p)


def test_load_config_valid_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent("""\
        defaults:
          image: vllm/vllm-openai:v0.4.0
          models_volume: /mnt/models
        models:
          coder:
            model: Qwen/Qwen2.5-Coder-32B-Instruct
            port: 8000
    """))
    cfg = load_config(p)
    assert cfg.defaults.image == "vllm/vllm-openai:v0.4.0"
    assert cfg.defaults.models_volume == "/mnt/models"
    assert cfg.models["coder"].port == 8000


# ---------------------------------------------------------------------------
# lookup_model
# ---------------------------------------------------------------------------


def test_lookup_existing_model():
    cfg = _make_config({"models": {"llama": {"model": "x/y", "port": 8000}}})
    entry = lookup_model(cfg, "llama")
    assert entry.model == "x/y"


def test_lookup_unknown_model_raises():
    cfg = _make_config({"models": {"llama": {"model": "x/y", "port": 8000}}})
    with pytest.raises(UnknownModelError, match="'mistral'"):
        lookup_model(cfg, "mistral")


def test_lookup_unknown_model_names_known_models():
    cfg = _make_config({"models": {"llama": {"model": "x/y", "port": 8000}}})
    with pytest.raises(UnknownModelError, match="llama"):
        lookup_model(cfg, "mistral")


# ---------------------------------------------------------------------------
# init — generate_init_yaml
# ---------------------------------------------------------------------------


def test_generate_init_yaml_is_valid_yaml():
    content = generate_init_yaml()
    parsed = yaml.safe_load(content)
    assert parsed is not None
    assert "defaults" in parsed
    assert "models" in parsed


def test_generate_init_yaml_contains_field_names():
    content = generate_init_yaml()
    for name in ("image", "gpus", "bind_address", "dtype", "extra_args", "model", "port"):
        assert name in content, f"Field '{name}' missing from init YAML template"


def test_generate_init_yaml_parseable_as_config():
    content = generate_init_yaml()
    cfg = Config.model_validate(yaml.safe_load(content))
    assert "my-model" in cfg.models
    assert cfg.models["my-model"].port == 8000
