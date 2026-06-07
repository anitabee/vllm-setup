from __future__ import annotations

import docker
from docker.errors import DockerException

from vllm_cli.errors import DockerUnavailableError

MANAGED_BY_LABEL = "managed-by"
MANAGED_BY_VALUE = "vllm-cli"
MODEL_NAME_LABEL = "model-name"


def _make_client() -> docker.DockerClient:
    try:
        client = docker.from_env()
        client.ping()
        return client
    except DockerException as exc:
        raise DockerUnavailableError(str(exc)) from exc


def list_running_model_names() -> set[str]:
    """Return the set of model names with a live running managed container."""
    client = _make_client()
    containers = client.containers.list(
        filters={
            "label": f"{MANAGED_BY_LABEL}={MANAGED_BY_VALUE}",
            "status": "running",
        }
    )
    return {
        c.labels[MODEL_NAME_LABEL]
        for c in containers
        if MODEL_NAME_LABEL in c.labels
    }
