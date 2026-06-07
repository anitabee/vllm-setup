from __future__ import annotations

import docker
from docker.errors import DockerException

from vllm_cli.errors import DockerUnavailableError, OperationError
from vllm_cli.models import ResolvedModel, RuntimeContainer

MANAGED_BY_LABEL = "managed-by"
MANAGED_BY_VALUE = "vllm-cli"
MODEL_NAME_LABEL = "model-name"


def _extract_port_binding(container) -> tuple[str, int] | None:
    for bindings in container.ports.values():
        if bindings:
            ip = bindings[0].get("HostIp") or "127.0.0.1"
            return ip, int(bindings[0]["HostPort"])
    return None


def _make_client() -> docker.DockerClient:
    try:
        client = docker.from_env()
        client.ping()
        return client
    except DockerException as exc:
        raise DockerUnavailableError(str(exc)) from exc


def list_runtime_containers() -> list[RuntimeContainer]:
    """Return a RuntimeContainer for each live managed container (readiness not yet checked)."""
    client = _make_client()
    containers = client.containers.list(
        filters={
            "label": f"{MANAGED_BY_LABEL}={MANAGED_BY_VALUE}",
            "status": "running",
        }
    )
    result: list[RuntimeContainer] = []
    for c in containers:
        model = c.labels.get(MODEL_NAME_LABEL, "")
        binding = _extract_port_binding(c)
        if binding is None:
            continue
        bind_address, port = binding
        base_url = f"http://{bind_address}:{port}/v1"
        result.append(
            RuntimeContainer(
                name=c.name,
                model=model,
                port=port,
                bind_address=bind_address,
                status=c.status,
                base_url=base_url,
                readiness="loading",
            )
        )
    return result


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


def stream_container_logs(name: str) -> None:
    """Stream logs for the managed container of model `name` to stdout.

    Raises UnknownContainerError if no running container is found for the model.
    Ctrl-C (KeyboardInterrupt) is allowed to propagate so the caller can exit cleanly.
    """
    from vllm_cli.errors import UnknownContainerError

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
            raise UnknownContainerError(name)
        container = containers[0]
        for chunk in container.logs(stream=True, follow=True):
            print(chunk.decode("utf-8", errors="replace"), end="", flush=True)
    except DockerException as exc:
        raise OperationError(str(exc)) from exc


def _device_request(gpus: str) -> docker.types.DeviceRequest:
    if gpus == "all":
        return docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])
    device_ids = [g.strip() for g in gpus.split(",")]
    return docker.types.DeviceRequest(device_ids=device_ids, capabilities=[["gpu"]])


def start_model(rm: ResolvedModel) -> RuntimeContainer:
    """Launch a vLLM container for *rm* and return immediately (non-blocking)."""
    client = _make_client()
    try:
        labels = {
            MANAGED_BY_LABEL: MANAGED_BY_VALUE,
            MODEL_NAME_LABEL: rm.name,
        }

        volumes: dict[str, dict] = {}
        if rm.models_volume:
            volumes[rm.models_volume] = {"bind": "/root/.cache/huggingface", "mode": "rw"}

        cmd: list[str] = [
            "--host", "0.0.0.0",
            "--port", "8000",
            "--model", rm.model,
            "--dtype", rm.dtype,
        ]
        if rm.tensor_parallel_size is not None:
            cmd += ["--tensor-parallel-size", str(rm.tensor_parallel_size)]
        if rm.max_model_len is not None:
            cmd += ["--max-model-len", str(rm.max_model_len)]
        cmd += rm.extra_args

        container = client.containers.run(
            rm.image,
            command=cmd,
            detach=True,
            labels=labels,
            volumes=volumes,
            ports={"8000/tcp": (rm.bind_address, rm.port)},
            device_requests=[_device_request(rm.gpus)],
        )

        base_url = f"http://{rm.bind_address}:{rm.port}/v1"
        return RuntimeContainer(
            name=container.name,
            model=rm.name,
            port=rm.port,
            bind_address=rm.bind_address,
            status="running",
            base_url=base_url,
            readiness="loading",
        )
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
