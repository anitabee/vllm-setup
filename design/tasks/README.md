# vLLM CLI — Implementation Tasks

Vertical-slice (tracer-bullet) tasks derived from `../requirements`,
`../architecture.md`, and the CLI best-practices guide. Each slice cuts through
all layers (CLI → config/adapter → render → tests) and is demoable and
mergeable on its own. All slices are **AFK** — the architecture doc already
settled the design decisions (Docker SDK = Option A, library stack, module
layout), so none require a human decision.

## Order & dependencies

```
01 walking-skeleton-help-config   (no blockers)
02 config-schema-init             ← 01
03 list                           ← 02   creates docker_adapter (label reads) + hf_adapter (cache scan)
04 stop-stop-all                  ← 03
05 ps                             ← 03   adds health adapter
06 download                       ← 03   extends hf_adapter (fetch)
07 logs                           ← 03   extends docker_adapter (log stream)
08 start-restart                  ← 04   extends docker_adapter (run) + adds ports.py; restart = stop+start
```

Slice 03 (`list`) is the foundational read-side slice: as the first consumer of
both external read paths it creates `docker_adapter` (label-filtered discovery)
and `hf_adapter` (cache scan). Slices 04–07 reuse those; slice 08 adds the write
path (container creation) and port-collision lookup.

## Command coverage

| Command | Slice |
| --- | --- |
| `help config` | 01 |
| `init` | 02 |
| `list` | 03 |
| `stop`, `stop-all` | 04 |
| `ps` | 05 |
| `download` (+ no-arg) | 06 |
| `logs` | 07 |
| `start`, `restart` | 08 |

## Tasks

1. [Walking skeleton + `help config`](01-walking-skeleton-help-config.md)
2. [Config schema, validation & `init`](02-config-schema-init.md)
3. [`list`](03-list.md)
4. [`stop` / `stop-all`](04-stop-stop-all.md)
5. [`ps`](05-ps.md)
6. [`download`](06-download.md)
7. [`logs`](07-logs.md)
8. [`start` + `restart`](08-start-restart.md)
