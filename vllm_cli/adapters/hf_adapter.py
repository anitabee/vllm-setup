from __future__ import annotations

from pathlib import Path
from typing import Optional

from huggingface_hub import scan_cache_dir


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
