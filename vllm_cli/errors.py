from __future__ import annotations


class VllmCliError(Exception):
    pass


class ConfigError(VllmCliError):
    pass


class UnknownModelError(ConfigError):
    pass


class PortCollisionError(VllmCliError):
    pass


class DockerUnavailableError(VllmCliError):
    pass


class OperationError(VllmCliError):
    pass


class DownloadError(VllmCliError):
    pass


# Maps exception type to exit code. Checked in isinstance order — most-specific first.
_EXIT_CODE_MAP: list[tuple[type[VllmCliError], int]] = [
    (UnknownModelError, 2),
    (ConfigError, 2),
    (PortCollisionError, 3),
    (DockerUnavailableError, 4),
    (OperationError, 5),
    (DownloadError, 6),
]


def exit_code_for(exc: VllmCliError) -> int:
    for exc_type, code in _EXIT_CODE_MAP:
        if isinstance(exc, exc_type):
            return code
    return 1
