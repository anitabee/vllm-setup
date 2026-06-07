from vllm_cli.errors import (
    ConfigError,
    DockerUnavailableError,
    DownloadError,
    OperationError,
    PortCollisionError,
    UnknownModelError,
    VllmCliError,
    exit_code_for,
)


def test_unknown_model_exit_code():
    assert exit_code_for(UnknownModelError("x")) == 2


def test_config_error_exit_code():
    assert exit_code_for(ConfigError("bad yaml")) == 2


def test_port_collision_exit_code():
    assert exit_code_for(PortCollisionError("8001")) == 3


def test_docker_unavailable_exit_code():
    assert exit_code_for(DockerUnavailableError()) == 4


def test_operation_error_exit_code():
    assert exit_code_for(OperationError("failed")) == 5


def test_download_error_exit_code():
    assert exit_code_for(DownloadError("net error")) == 6


def test_unknown_error_exit_code():
    class OtherError(VllmCliError):
        pass

    assert exit_code_for(OtherError()) == 1


def test_subclass_resolution():
    # UnknownModelError is a subclass of ConfigError but must resolve to 2 (same code, most specific first).
    exc = UnknownModelError("laguna-xs")
    assert exit_code_for(exc) == 2
    assert isinstance(exc, ConfigError)
