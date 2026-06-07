# 02 — Config schema, validation & `init`

**Type:** AFK

## What to build

The config layer end to end: load `config.yaml` from the current working
directory, validate it, merge `defaults` into each model to produce fully
resolved domain objects, and generate a starter config with `init`. This is the
data foundation every Docker-touching command builds on.

Scope:

- Pydantic v2 models in `config.py`/`models.py`:
  - `Defaults` — `image`, `gpus`, `bind_address`, `models_volume`, `dtype`,
    `extra_args`.
  - `ModelEntry` — `model` (required), `port` (required), `served_name`, plus
    optional overrides of any `Defaults` field and `tensor_parallel_size`,
    `max_model_len`.
  - `Config` — `defaults` + `models: dict[str, ModelEntry]`, hosting
    whole-config validators.
- YAML load via PyYAML, validated through Pydantic before any other work.
- Validation (runs on every command that reads config, before any action):
  required `model`/`port` per model; duplicate-port scan across all models
  failing with an error that names each conflicting model and the shared port;
  unknown-model-name lookup helper for commands taking `<name>`.
- A resolver producing `ResolvedModel` per model (defaults merged with the
  model's own fields, model wins on conflict; unset-everywhere fields omitted so
  vLLM uses its own default). Downstream code only ever sees `ResolvedModel`.
- `init` command: writes `config.yaml` with the `defaults` block and one or two
  placeholder models, including inline comments rendered from the **shared field
  reference** from slice 01. Refuses to overwrite an existing file unless
  `--force`.

## Acceptance criteria

- [ ] Valid `config.yaml` loads into a `Config`; each model resolves to a
      `ResolvedModel` with defaults correctly overridden by per-model fields.
- [ ] Missing `model` or `port` fails with exit code 2 naming the file and the
      specific problem.
- [ ] Two models sharing a port fail with exit code 2, naming each conflicting
      model and the shared port.
- [ ] An unknown `<name>` lookup raises the typed error mapped to exit code 2.
- [ ] `vllm-cli init` writes a commented `config.yaml`; comments come from the
      same source as `help config`. Re-running without `--force` refuses to
      overwrite (exit non-zero); `--force` overwrites.
- [ ] Config tests cover the defaults/override merge, required-field
      enforcement, and the duplicate-port validator — all pure, no Docker.

## Blocked by

- 01 — Walking skeleton + `help config`
