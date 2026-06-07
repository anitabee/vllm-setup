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


class UnknownContainerError(VllmCliError):
    """Raised when no running managed container exists for the given model name."""

    def __init__(self, model_name: str) -> None:
        super().__init__(f"No running container for model '{model_name}'")
        self.model_name = model_name


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
