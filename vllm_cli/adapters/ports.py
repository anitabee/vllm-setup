from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass
class PortOccupant:
    managed_model: str | None  # set when a CLI-managed container owns the port
    pid: int | None
    process_name: str | None


def find_port_occupant(port: int) -> PortOccupant | None:
    """Return who is listening on *port*, or None if the port is free.

    Managed containers are checked first so docker-proxy PIDs don't surface as
    unmanaged occupants when one of our own containers holds the port.
    """
    from vllm_cli.adapters import docker_adapter as _docker

    try:
        for c in _docker.list_runtime_containers():
            if c.port == port:
                return PortOccupant(managed_model=c.model, pid=None, process_name=None)
    except Exception:
        pass

    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.status == "LISTEN":
                pid = conn.pid
                name: str | None = None
                if pid:
                    try:
                        name = psutil.Process(pid).name()
                    except psutil.NoSuchProcess:
                        pass
                return PortOccupant(managed_model=None, pid=pid, process_name=name)
    except psutil.AccessDenied:
        pass

    return None
