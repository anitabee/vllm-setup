# 08 — `start` + `restart`

**Type:** AFK

## What to build

The core launch path, plus its `restart` convenience wrapper. Resolves a model's
effective config, guards against port collisions, launches a labelled vLLM
container with full GPU/volume/arg wiring, and returns immediately with
connection info (it does **not** wait for the model to finish loading — readiness
is reported separately by `ps`). Extends `docker_adapter` (created in slice 03)
with container creation and adds the `ports.py` collision-lookup adapter.

`start <name>` steps:

1. Validate `<name>` exists in config.
2. Resolve the effective `ResolvedModel`.
3. Check the host port. If in use, do not start; error and identify the
   occupant — if it's a CLI-managed container, name the managed model
   (e.g. "port 8001 taken by managed model laguna-xs"); otherwise show the raw
   PID and process name.
4. Otherwise launch the container:
   - labels `managed-by` and `model-name=<name>`;
   - mount `models_volume` as the HF cache;
   - bind the API to the resolved `bind_address` and `port`;
   - pass GPUs via `docker.types.DeviceRequest` (derived from the `gpus` field),
     plus `dtype`, `tensor_parallel_size`, `max_model_len`, and `extra_args` as
     applicable.
5. Return as soon as the container is up, printing connection info immediately.

`restart <name>` = `stop <name>` then `start <name>`.

Scope:

- `adapters/docker_adapter.py` — container creation (labels, volume mount, port
  binding, `DeviceRequest`, dtype/tp/max_model_len/extra_args).
- `adapters/ports.py` — psutil-based host-port → PID/process lookup, and the
  managed-vs-unmanaged determination for the collision message.
- `render.py` — the immediate connection-info output.
- `restart` command composing existing `stop` (slice 04) and `start`.

## Acceptance criteria

- [ ] `vllm-cli start <name>` launches a container labelled `managed-by` +
      `model-name=<name>`, with `models_volume` mounted, API bound to the
      resolved `bind_address:port`, and GPUs/dtype/tensor_parallel_size/
      max_model_len/extra_args applied as configured.
- [ ] The command returns immediately (does not block on model load) and prints
      the base URL `http://<bind_address>:<port>/v1`.
- [ ] Unknown `<name>` → exit code 2.
- [ ] Port already in use → exit code 3; message names a managed model if the
      occupant is CLI-managed, otherwise shows the raw PID and process name.
- [ ] Docker daemon unreachable → exit code 4; container/operation failure →
      exit code 5.
- [ ] `vllm-cli restart <name>` stops then starts the model.
- [ ] Command tests with fake Docker/ports adapters verify the labels and run
      arguments, both collision branches (managed vs PID/process), and the
      restart composition — no Docker, GPU, or network.

## Blocked by

- 04 — `stop` / `stop-all` (provides `stop` for `restart`; transitively 03, 02)
