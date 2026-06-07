# 04 — `stop` / `stop-all`

**Type:** AFK

## What to build

Teardown of managed containers, end to end. Extends `docker_adapter` (created in
slice 03) with stop + remove, scoped strictly to CLI-managed containers via the
`managed-by` label so other Docker workloads on the host are never touched.

(`restart` is intentionally **not** here — it composes `stop` + `start` and
lands with `start` in slice 08.)

Scope:

- `stop <name>`: validate the name against config, then stop and remove that
  model's container. Idempotent — stopping a model that isn't running reports
  that plainly rather than erroring hard.
- `stop-all`: stop and remove all containers filtered by the `managed-by` label.
  Without flags, graceful stop then remove; with `--force`, kill immediately
  then remove.
- Report what changed (which containers were stopped/removed), per the
  "tell users when you change state" practice.

## Acceptance criteria

- [ ] `vllm-cli stop <name>` stops and removes that model's container and reports
      it; unknown `<name>` fails with exit code 2.
- [ ] `stop` of a model with no running container reports the no-op clearly and
      does not error.
- [ ] `vllm-cli stop-all` stops and removes only `managed-by` containers, never
      unmanaged Docker workloads.
- [ ] `stop-all --force` kills immediately then removes.
- [ ] Docker daemon unreachable → exit code 4; operation failure → exit code 5.
- [ ] Command tests with mocked Docker adapter verify label filtering, the
      `--force` branch, and that no unmanaged containers are touched.

## Blocked by

- 03 — `list` (creates `docker_adapter` + label conventions)
