# vLLM CLI — Architecture

## 1. Context and goals

This document describes the technical design of the vLLM CLI defined in the requirements doc. The tool manages local vLLM Docker containers, one per model, driven by a YAML registry, and reports how to connect to each. This document covers the library stack, how the code is decomposed into modules, the data model, key decisions, error handling, packaging, and testing.

Design priorities, in order: correctness and predictable behavior, clear separation between user-facing output and internal logic, and testability without requiring a GPU or a running Docker daemon.

## 2. Technology stack

| Library | Purpose |
| --- | --- |
| Typer | CLI framework. Defines the command surface, parses arguments and flags, generates help, and maps each command to a handler. |
| Pydantic v2 | Config schema, type validation, required-field enforcement, the defaults-with-override merge, and the colliding-port validator. |
| PyYAML | Reads `config.yaml` into a dict for Pydantic, and writes the placeholder file for `init`. |
| Docker SDK for Python (`docker`) | All container lifecycle and runtime inspection: create with labels, mount the cache volume, set bind address and ports, pass GPU access via `DeviceRequest`, list and filter by label, stop, remove, and stream logs. |
| psutil | Maps an occupied host port to its owning PID and process name during a `start` collision. |
| huggingface_hub | `snapshot_download` for the `download` command, `scan_cache_dir` for `Downloaded` / `not downloaded` detection in `list`. |
| httpx | GETs each running model's `/health` endpoint for the `ps` readiness state. |
| Rich | Terminal rendering: the `ps` table, the `list` view with download labels and flush-right `RUNNING`, status colors, error output, and the `download` progress display. |
| `logging` + `rich.logging.RichHandler` | Diagnostic logging, kept separate from user-facing command output, rendered through Rich. |
| pytest | Tests against mocked adapters so CLI logic, validation, and rendering run without Docker, a GPU, or network. |
| pyproject.toml + uv | Packaging, the `vllm-cli` console entry point, pinned dependencies, reproducible environment. |

## 3. Module decomposition

The codebase separates the entry layer, the domain logic, and the external-system adapters. Adapters are thin and isolate every side effect (Docker, the filesystem cache, the network, the host process table), which is what makes the rest testable.

```
vllm_cli/
  __init__.py
  cli.py              # Typer app and command handlers (entry layer)
  config.py           # Pydantic models, YAML load, validation, defaults merge
  models.py           # Resolved domain objects (ResolvedModel, RuntimeContainer)
  adapters/
    docker_adapter.py # Docker SDK wrapper: run, stop, remove, list, logs
    hf_adapter.py     # huggingface_hub wrapper: download, cache scan
    ports.py          # psutil-based port-to-process lookup
    health.py         # httpx /health polling
  render.py           # Rich rendering for list, ps, download progress, errors
  logging_setup.py    # logging config with RichHandler
  errors.py           # Exception types and exit-code mapping
```

Dependency direction is one-way. `cli.py` orchestrates by calling `config`, the adapters, and `render`. Adapters depend only on their external library and the domain objects in `models.py`. Nothing imports `cli.py`. This keeps the command handlers thin: parse, call config, call adapters, hand results to render.

### Responsibilities

- **cli.py** — One Typer command per requirement. Handlers contain orchestration only, no Docker or YAML logic. They translate adapter results into render calls and map exceptions to exit codes.
- **config.py** — Loads `config.yaml`, validates it with Pydantic, runs the colliding-port check, and exposes a resolver that merges `defaults` into each model to produce `ResolvedModel` objects. Every command that needs config goes through here.
- **models.py** — Plain typed objects passed between layers: `ResolvedModel` (the fully-populated effective config for one model) and `RuntimeContainer` (a managed container's live state as read from Docker plus a readiness flag).
- **docker_adapter.py** — The only module that imports `docker`. Owns label conventions, container creation including `DeviceRequest` for GPUs, volume mounts, port bindings, lifecycle, label-filtered listing, and log streaming.
- **hf_adapter.py** — The only module that imports `huggingface_hub`. Downloads into `models_volume` and reports per-model download status from the cache scan.
- **ports.py** — Resolves a host port to a process via psutil and returns enough to build the collision message.
- **health.py** — Polls `/health` over httpx and returns a readiness state.
- **render.py** — All Rich output. Keeping rendering here means logic modules never print, which keeps them testable and keeps output consistent.

## 4. Data model

Two Pydantic config models and two domain objects.

**Config models (parsed from YAML):**

- `Defaults` — `image`, `gpus`, `bind_address`, `models_volume`, `dtype`, `extra_args`.
- `ModelEntry` — `model` (required), `port` (required), `served_name`, plus optional overrides of any `Defaults` field and `tensor_parallel_size`, `max_model_len`.
- `Config` — `defaults: Defaults` and `models: dict[str, ModelEntry]`. Hosts the whole-config validators, including the duplicate-port check across all entries.

**Resolved domain object:**

- `ResolvedModel` — produced by merging `Defaults` with one `ModelEntry`. Every field is populated to a concrete value (or explicitly absent where vLLM should use its own default). This is what `docker_adapter` consumes to build a `run` call, so the adapter never sees raw config or merge logic.

**Runtime object:**

- `RuntimeContainer` — built from a Docker container plus a health check: `name`, `model`, `port`, `bind_address`, container `status`, `base_url`, and `readiness` (`loading` or `ready`). This is what `ps` renders.

The flow is: YAML → `Config` (validated) → `ResolvedModel` per model → adapter actions → `RuntimeContainer` for display. Validation and merging happen once, early, so downstream code only ever sees fully-formed objects.

## 5. Decision: Docker access via the SDK (Option A)

**Decision.** Use the Docker SDK for Python for all Docker interaction, including container creation.

**Context.** The alternative was shelling out to the `docker` CLI via subprocess. The SDK gives typed objects, native label filtering, and clean log streaming, which suit lifecycle and label-driven discovery (`list`, `ps`, `stop-all`). The subprocess approach makes GPU flags trivial but forces text parsing for inspection and loses type safety.

**Consequences.** GPU passthrough is expressed with `docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])` (or specific device ids derived from the `gpus` field) rather than a plain `--gpus all` string. This is slightly more verbose and is the one rough edge of the SDK, but it is contained entirely within `docker_adapter` and does not leak into the rest of the code. In exchange, every inspection path works with typed objects and label filters instead of parsed CLI output. The NVIDIA container toolkit must be installed on the host, which the requirements already assume.

## 6. Error handling and exit codes

A small set of exception types in `errors.py`, raised by config and adapters, caught in `cli.py`, and mapped to exit codes and Rich-rendered messages. User-facing errors are concise; full detail goes to the log via `RichHandler`.

| Condition | Exit code | Message |
| --- | --- | --- |
| Success | 0 | Normal output |
| Config invalid (missing field, duplicate port, parse error) | 2 | Names the file and the specific problem |
| Unknown model name | 2 | States the name is not in the config |
| Port collision on `start` | 3 | Names the occupant: managed model, or raw PID and process name |
| Docker daemon unreachable | 4 | States the daemon is unavailable |
| Container or operation failure | 5 | Surfaces the Docker error |
| Download failure | 6 | Surfaces the download error, notes it is re-runnable |

Logic modules raise typed exceptions and never call `sys.exit`. The exit-code mapping lives only at the CLI boundary.

## 7. Packaging and project layout

- `pyproject.toml` with the package metadata and a `[project.scripts]` entry exposing `vllm-cli`.
- uv for the environment and lockfile, giving reproducible installs.
- Dependencies pinned to compatible ranges and locked.
- The `init` command's placeholder config and the `help config` field reference share a single source of field documentation so the two cannot drift.

## 8. Testing approach

- Adapters are thin and sit behind clear function signatures, so tests substitute fakes for `docker`, `huggingface_hub`, psutil, and httpx. The CLI then runs end to end in tests without Docker, a GPU, or the network.
- **Config tests** cover the merge of defaults and overrides, required-field enforcement, and the duplicate-port validator, all pure and fast.
- **Render tests** assert on the structure of the `list` and `ps` output, including the download labels and the flush-right `RUNNING` marker.
- **Command tests** use Typer's `CliRunner` against mocked adapters to verify orchestration, exit codes, and error messages for each command, including the port-collision branch and the no-argument form of `download`.
- A small optional set of integration tests can run against a real Docker daemon for the lifecycle path, kept separate so the default test run needs no daemon.