from __future__ import annotations

import docker
from docker.errors import DockerException

from vllm_cli.errors import DockerUnavailableError, OperationError

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


def stop_model(name: str) -> bool:
    """Stop and remove the managed container for model `name`.

    Returns True if a container was stopped, False if none was running.
    """
    client = _make_client()
    try:
        containers = client.containers.list(
            filters={
                "label": [
                    f"{MANAGED_BY_LABEL}={MANAGED_BY_VALUE}",
                    f"{MODEL_NAME_LABEL}={name}",
                ],
                "status": "running",
            }
        )
        if not containers:
            return False
        for c in containers:
            c.stop()
            c.remove()
        return True
    except DockerException as exc:
        raise OperationError(str(exc)) from exc


def stop_all(force: bool = False) -> list[str]:
    """Stop and remove all managed containers.

    Returns the list of model names that were stopped.
    """
    client = _make_client()
    try:
        containers = client.containers.list(
            filters={"label": f"{MANAGED_BY_LABEL}={MANAGED_BY_VALUE}"}
        )
        stopped: list[str] = []
        for c in containers:
            model_name = c.labels.get(MODEL_NAME_LABEL, c.name)
            if force:
                c.kill()
            else:
                c.stop()
            c.remove()
            stopped.append(model_name)
        return stopped
    except DockerException as exc:
        raise OperationError(str(exc)) from exc
