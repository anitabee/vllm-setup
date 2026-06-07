# 06 — `download` (+ no-arg list of undownloaded)

**Type:** AFK

## What to build

Pre-download a model's weights into the shared `models_volume` HF cache,
separately from `start`, so the slow first-run download is isolated and shows
interactive progress in the terminal rather than buried in container logs. A
later `start` of that model is then fast and consistent; an interrupted download
is simply re-run. Extends `hf_adapter` (created in slice 03) with the fetch path
and reuses its cache scan to decide what is "available to download".

Scope:

- `download <name>`: validate the name against config, then download that model
  into `models_volume`. Use the HF download path (e.g. `snapshot_download` /
  `hf download <model>`) targeting `models_volume`;
  `HF_HUB_ENABLE_HF_TRANSFER=1` may be set for the faster backend.
- `download` (no argument): list configured models not yet present in the cache
  (the models available to download); already-downloaded models are omitted.
- `render.py` — interactive Rich progress display for the download.

## Acceptance criteria

- [ ] `vllm-cli download <name>` fetches the model's weights into
      `models_volume` with visible progress; unknown `<name>` → exit code 2.
- [ ] Re-running after an interrupted download resumes/repeats cleanly and
      succeeds (re-runnable).
- [ ] `vllm-cli download` with no argument lists only not-yet-downloaded
      configured models, omitting downloaded ones.
- [ ] After a successful download, `list` reports that model as `Downloaded`.
- [ ] Download failure → exit code 6, with a message noting it is re-runnable.
- [ ] Command tests with a fake HF adapter verify the no-arg listing and the
      named-download path without network.

## Blocked by

- 03 — `list` (creates `hf_adapter` + cache scan)
