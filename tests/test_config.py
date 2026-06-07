from vllm_cli.config import FIELD_REFERENCE


def test_all_required_fields_present():
    names = {f.name for f in FIELD_REFERENCE}
    required = {"image", "gpus", "bind_address", "models_volume", "dtype", "extra_args",
                "model", "port", "served_name", "tensor_parallel_size", "max_model_len"}
    assert required == names


def test_per_model_required_fields_marked():
    scopes = {f.name: f.scope for f in FIELD_REFERENCE}
    assert "required" in scopes["model"]
    assert "required" in scopes["port"]


def test_field_reference_non_empty_descriptions():
    for f in FIELD_REFERENCE:
        assert f.meaning.strip(), f"{f.name} has empty meaning"
        assert f.values_default.strip(), f"{f.name} has empty values_default"
