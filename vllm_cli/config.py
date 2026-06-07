from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ValidationError, model_validator

from vllm_cli.errors import ConfigError, UnknownModelError
from vllm_cli.models import ResolvedModel


@dataclass(frozen=True)
class FieldInfo:
    name: str
    scope: str
    meaning: str
    values_default: str


# Single source of truth for the configuration field reference (requirements §4.4).
# Both `help config` and `init` render from this list so the two can never drift.
FIELD_REFERENCE: list[FieldInfo] = [
    FieldInfo(
        name="image",
        scope="default + per-model",
        meaning="vLLM Docker image and tag. Pin a tag for reproducibility.",
        values_default="vllm/vllm-openai:latest",
    ),
    FieldInfo(
        name="gpus",
        scope="default + per-model",
        meaning="Devices exposed to the container, mapped to `docker --gpus`.",
        values_default="all, 0, 0,1  |  default: all",
    ),
    FieldInfo(
        name="bind_address",
        scope="default + per-model",
        meaning="Host interface the API binds to. 127.0.0.1 = local only; 0.0.0.0 = exposed to LAN (unauthenticated).",
        values_default="default: 127.0.0.1",
    ),
    FieldInfo(
        name="models_volume",
        scope="default + per-model",
        meaning="Host path mounted into the container as the Hugging Face cache. Shared across models so weights download once.",
        values_default="Any host path",
    ),
    FieldInfo(
        name="dtype",
        scope="default + per-model",
        meaning="Model precision passed to vLLM.",
        values_default="auto, float16, bfloat16, …  |  default: auto",
    ),
    FieldInfo(
        name="extra_args",
        scope="default + per-model",
        meaning="Raw flags appended to the vLLM command for anything not modelled above.",
        values_default="List of strings  |  default: []",
    ),
    FieldInfo(
        name="model",
        scope="per-model (required)",
        meaning="Hugging Face repo id or local path for the model weights.",
        values_default="e.g. Qwen/Qwen2.5-Coder-32B-Instruct",
    ),
    FieldInfo(
        name="port",
        scope="per-model (required)",
        meaning="Unique host port for this model's OpenAI-compatible API. Must not collide with any other entry.",
        values_default="Any free port",
    ),
    FieldInfo(
        name="served_name",
        scope="per-model",
        meaning="Model id that clients send in requests. Defaults to the value of `model`.",
        values_default="defaults to model",
    ),
    FieldInfo(
        name="tensor_parallel_size",
        scope="per-model",
        meaning="Number of GPUs to shard the model across.",
        values_default="Integer  |  default: 1",
    ),
    FieldInfo(
        name="max_model_len",
        scope="per-model",
        meaning="Maximum context length. Omit to let vLLM use the model's own default.",
        values_default="Integer  |  omit for model default",
    ),
]

_FIELD_BY_NAME: dict[str, FieldInfo] = {f.name: f for f in FIELD_REFERENCE}


# ---------------------------------------------------------------------------
# Pydantic config models
# ---------------------------------------------------------------------------


class Defaults(BaseModel):
    image: str = "vllm/vllm-openai:latest"
    gpus: str = "all"
    bind_address: str = "127.0.0.1"
    models_volume: Optional[str] = None
    dtype: str = "auto"
    extra_args: list[str] = []


class ModelEntry(BaseModel):
    model: str
    port: int
    served_name: Optional[str] = None
    tensor_parallel_size: Optional[int] = None
    max_model_len: Optional[int] = None
    # per-model overrides for any Defaults field
    image: Optional[str] = None
    gpus: Optional[str] = None
    bind_address: Optional[str] = None
    models_volume: Optional[str] = None
    dtype: Optional[str] = None
    extra_args: Optional[list[str]] = None


class Config(BaseModel):
    defaults: Defaults = Defaults()
    models: dict[str, ModelEntry]

    @model_validator(mode="after")
    def _check_duplicate_ports(self) -> "Config":
        seen: dict[int, str] = {}
        conflicts: list[str] = []
        for name, entry in self.models.items():
            if entry.port in seen:
                conflicts.append(
                    f"'{seen[entry.port]}' and '{name}' both use port {entry.port}"
                )
            else:
                seen[entry.port] = name
        if conflicts:
            raise ValueError("; ".join(conflicts))
        return self


# ---------------------------------------------------------------------------
# Load & validate
# ---------------------------------------------------------------------------


def load_config(path: Path) -> Config:
    try:
        raw = yaml.safe_load(path.read_text())
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}")
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML parse error in {path}: {exc}")
    if raw is None:
        raise ConfigError(f"Config file is empty: {path}")
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        msgs: list[str] = []
        for err in exc.errors():
            loc = " → ".join(str(p) for p in err["loc"]) if err["loc"] else "config"
            msgs.append(f"{path}: [{loc}] {err['msg']}")
        raise ConfigError("\n".join(msgs)) from exc


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def resolve_model(name: str, entry: ModelEntry, defaults: Defaults) -> ResolvedModel:
    """Merge defaults with per-model overrides; model wins on conflict."""
    return ResolvedModel(
        name=name,
        model=entry.model,
        port=entry.port,
        image=entry.image if entry.image is not None else defaults.image,
        gpus=entry.gpus if entry.gpus is not None else defaults.gpus,
        bind_address=entry.bind_address if entry.bind_address is not None else defaults.bind_address,
        models_volume=entry.models_volume if entry.models_volume is not None else defaults.models_volume,
        dtype=entry.dtype if entry.dtype is not None else defaults.dtype,
        extra_args=entry.extra_args if entry.extra_args is not None else list(defaults.extra_args),
        served_name=entry.served_name,
        tensor_parallel_size=entry.tensor_parallel_size,
        max_model_len=entry.max_model_len,
    )


def resolve_all(config: Config) -> dict[str, ResolvedModel]:
    return {name: resolve_model(name, entry, config.defaults) for name, entry in config.models.items()}


def lookup_model(config: Config, name: str) -> ModelEntry:
    try:
        return config.models[name]
    except KeyError:
        known = ", ".join(f"'{k}'" for k in config.models)
        raise UnknownModelError(f"Unknown model '{name}'. Known models: {known}")


# ---------------------------------------------------------------------------
# Init template
# ---------------------------------------------------------------------------


def _commented(field_name: str, indent: str = "  ") -> str:
    f = _FIELD_BY_NAME[field_name]
    return f"{indent}# {f.meaning}\n{indent}# Values/Default: {f.values_default}"


def generate_init_yaml() -> str:
    lines: list[str] = [
        "# vllm-cli configuration",
        "# Edit this file to add or modify model configurations.",
        "",
        "defaults:",
        _commented("image"),
        "  image: vllm/vllm-openai:latest",
        "",
        _commented("gpus"),
        "  gpus: all",
        "",
        _commented("bind_address"),
        "  bind_address: 127.0.0.1",
        "",
        _commented("models_volume"),
        "  # models_volume: /path/to/models",
        "",
        _commented("dtype"),
        "  dtype: auto",
        "",
        _commented("extra_args"),
        "  extra_args: []",
        "",
        "models:",
        "  my-model:",
        _commented("model", indent="    "),
        "    model: Qwen/Qwen2.5-Coder-32B-Instruct",
        "",
        _commented("port", indent="    "),
        "    port: 8000",
        "",
        _commented("served_name", indent="    "),
        "    # served_name: my-model",
        "",
        _commented("tensor_parallel_size", indent="    "),
        "    # tensor_parallel_size: 1",
        "",
        _commented("max_model_len", indent="    "),
        "    # max_model_len: 4096",
        "",
    ]
    return "\n".join(lines)
