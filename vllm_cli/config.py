from __future__ import annotations

from dataclasses import dataclass


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
