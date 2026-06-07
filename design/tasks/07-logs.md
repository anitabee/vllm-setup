# 07 — `logs`

**Type:** AFK

## What to build

Tail a model container's logs — the primary way to watch model-loading progress
and diagnose OOM or startup failures. On a first-ever `start`, the Hugging Face
download progress also appears here, since that download runs inside the
container and writes to its logs. Extends `docker_adapter` (created in slice 03)
with log streaming.

Scope:

- `logs <name>`: validate the name against config, locate the model's
  `managed-by` container, and stream/tail its logs.
- Log output streams to stdout so it can be piped; Ctrl-C exits cleanly without
  trapping the signal.

## Acceptance criteria

- [ ] `vllm-cli logs <name>` tails the named model's container logs; unknown
      `<name>` → exit code 2.
- [ ] `logs` for a model with no running container reports that clearly rather
      than hanging or dumping a stack trace.
- [ ] Output goes to stdout and is pipeable; Ctrl-C stops the tail cleanly.
- [ ] Docker daemon unreachable → exit code 4.
- [ ] Command tests with a fake Docker adapter verify the stream is requested
      for the correct container and the no-container branch is handled.

## Blocked by

- 03 — `list` (creates `docker_adapter` + label conventions)
