from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from huggingface_hub import scan_cache_dir, snapshot_download

from vllm_cli.errors import DownloadError


def list_downloaded_models(cache_dir: Optional[str]) -> set[str]:
    """Return the set of HF repo_ids present in the cache at cache_dir."""
    if cache_dir is None:
        return set()
    cache_path = Path(cache_dir)
    if not cache_path.is_dir():
        return set()
    try:
        info = scan_cache_dir(cache_path)
        return {repo.repo_id for repo in info.repos if repo.repo_type == "model"}
    except Exception:
        return set()


def download_model(repo_id: str, cache_dir: str) -> None:
    """Download model weights into cache_dir using the HF cache layout.

    Sets HF_HUB_ENABLE_HF_TRANSFER=1 for faster downloads when hf_transfer is
    installed. Raises DownloadError on any failure; re-running is always safe
    because snapshot_download resumes partial downloads.
    """
    prev = os.environ.get("HF_HUB_ENABLE_HF_TRANSFER")
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
    try:
        snapshot_download(repo_id=repo_id, cache_dir=cache_dir)
    except Exception as exc:
        raise DownloadError(f"Failed to download '{repo_id}': {exc}") from exc
    finally:
        if prev is None:
            os.environ.pop("HF_HUB_ENABLE_HF_TRANSFER", None)
        else:
            os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = prev
