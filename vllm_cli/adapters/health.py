from __future__ import annotations

import httpx


def check_readiness(base_url: str, timeout: float = 3.0) -> str:
    """GET <base_url>/health; return 'ready' on 200, 'loading' otherwise."""
    try:
        resp = httpx.get(f"{base_url}/health", timeout=timeout)
        if resp.status_code == 200:
            return "ready"
    except Exception:
        pass
    return "loading"
