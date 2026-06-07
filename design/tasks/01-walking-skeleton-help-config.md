# 01 — Walking skeleton + `help config`

**Type:** AFK

## What to build

The first end-to-end tracer through the whole stack: a packaged, installable
`vllm-cli` Typer application that runs, prints help, reports its version, and
serves the in-CLI schema documentation via `help config`. No Docker, no config
parsing yet — this slice establishes the project skeleton, the CLI contract,
the error→exit-code boundary, and the test harness that every later slice
reuses.

It also creates the **single source of field documentation** (the section 4.4
field reference) as a data structure. `help config` renders it now; slice 02's
`init` will render the same source into a commented template so the two can
never drift.

Scope:

- `pyproject.toml` + `uv` lockfile, `[project.scripts]` exposing `vllm-cli`,
  dependencies pinned to compatible ranges (Typer, Pydantic v2, PyYAML,
  docker, psutil, huggingface_hub, httpx, Rich; pytest as dev dep).
- Module skeleton per the architecture: `cli.py`, `config.py`, `models.py`,
  `render.py`, `logging_setup.py`, `errors.py`, and an `adapters/` package
  (empty stubs are fine where a later slice fills them in).
- `errors.py`: the exception hierarchy and the single exit-code mapping table
  (0 success, 2 config/usage, 3 port collision, 4 docker unreachable,
  5 operation failure, 6 download failure). Logic never calls `sys.exit`; the
  mapping is applied only at the `cli.py` boundary.
- `logging_setup.py`: `logging` + `rich.logging.RichHandler`, diagnostic logs
  on **stderr**, kept separate from user-facing command output on stdout.
- `render.py`: Rich console wiring with TTY/`NO_COLOR`/`--no-color` color
  detection.
- The shared field-reference data structure + `help config` command that prints
  every field, its scope, meaning, and accepted values/default.
- pytest harness using Typer's `CliRunner`.

## Acceptance criteria

- [ ] `uv`-installed `vllm-cli` console entry point runs and exits 0.
- [ ] `vllm-cli`, `vllm-cli --help`, `vllm-cli -h`, and `vllm-cli help` all show
      top-level help listing the command surface; `--version` prints the version.
- [ ] `vllm-cli help config` prints the full section-4.4 field reference (field,
      scope, meaning, values/default) sourced from the shared structure.
- [ ] Errors render concisely on stderr; the documented exit-code mapping is
      applied only at the CLI boundary, with logic modules raising typed
      exceptions instead of exiting.
- [ ] Primary output goes to stdout, diagnostics/errors to stderr; color is
      disabled when stdout is not a TTY, when `NO_COLOR` is set, or with
      `--no-color`.
- [ ] A `--no-input` global flag exists and forces non-interactive behavior.
- [ ] `pytest` runs green with no Docker daemon, GPU, or network, driving the
      CLI through `CliRunner`.

## Blocked by

- None — can start immediately.
