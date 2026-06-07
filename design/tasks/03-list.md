# 03 — `list` (registry view + download status + RUNNING)

**Type:** AFK

## What to build

The registry view, and the foundational **read-side** slice: it is the first
consumer of both external read paths and therefore creates them for everyone
downstream — the Docker label-filtered container discovery and the Hugging Face
cache scan. `ps`, `download`, and `logs` reuse these.

`list` shows every configured model in the exact order it appears in the YAML.
For each model:

- the model name;
- a download status label — `Downloaded` if the model's weights are present in
  `models_volume`, otherwise `not downloaded`;
- `RUNNING` aligned flush-right when a live managed container exists for it;
  nothing in that position otherwise.

A model can appear here without appearing in `ps`. State is derived, never
tracked: download status from the HF cache layout under `models_volume`
(`models--<org>--<repo>` snapshot dirs), running status from Docker filtered on
the `managed-by` label.

Scope:

- `adapters/docker_adapter.py` — create the module; implement label-filtered
  listing of managed containers (the read path; owns the `managed-by` /
  `model-name` label conventions). Only module that imports `docker`.
- `adapters/hf_adapter.py` — create the module; implement the cache scan
  (`scan_cache_dir`) mapping configured models to Downloaded / not-downloaded.
  Only module that imports `huggingface_hub`.
- `render.py` — the `list` view with download labels and flush-right `RUNNING`.

## Acceptance criteria

- [ ] `vllm-cli list` prints configured models in YAML declaration order.
- [ ] Each line shows `Downloaded` or `not downloaded` based on a real scan of
      the HF cache under `models_volume`.
- [ ] `RUNNING` appears flush-right only for models with a live `managed-by`
      container; non-running models show nothing there.
- [ ] Works for models that are configured but never started (present in `list`,
      absent from any running set).
- [ ] If the Docker daemon is unreachable, fails with exit code 4 and a clear
      message.
- [ ] Render tests assert the output structure (download labels + flush-right
      `RUNNING`) against fake adapters; no Docker, GPU, or network needed.

## Blocked by

- 02 — Config schema, validation & `init`
