from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResolvedModel:
    """Fully-merged effective configuration for one model (defaults + per-model overrides)."""

    name: str
    model: str
    port: int
    image: str
    gpus: str
    bind_address: str
    models_volume: str
    dtype: str
    extra_args: list[str] = field(default_factory=list)
    served_name: Optional[str] = None
    tensor_parallel_size: Optional[int] = None
    max_model_len: Optional[int] = None


@dataclass
class RuntimeContainer:
    """Live state of a managed container, including a readiness flag from /health."""

    name: str
    model: str
    port: int
    bind_address: str
    status: str
    base_url: str
    readiness: str  # "loading" | "ready"
