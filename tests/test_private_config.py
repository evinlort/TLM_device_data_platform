import json

import pytest

from tlm_device_data_platform.private_config import load_private_config, write_private_config


def test_exclusive_owner_only_configuration(tmp_path):
    path = tmp_path / "device.secret.json"
    write_private_config(path, {"TLM_DEVICE_TOKEN": "test-only"})
    assert path.stat().st_mode & 0o777 == 0o600
    assert load_private_config(path, {"TLM_DEVICE_TOKEN"}) == {"TLM_DEVICE_TOKEN": "test-only"}
    with pytest.raises(FileExistsError):
        write_private_config(path, {"TLM_DEVICE_TOKEN": "replacement"})
    assert load_private_config(path, {"TLM_DEVICE_TOKEN"})["TLM_DEVICE_TOKEN"] == "test-only"


def test_public_permissions_and_symlinks_are_rejected(tmp_path):
    path = tmp_path / "config.secret.json"
    write_private_config(path, {"key": "value"})
    path.chmod(0o644)
    with pytest.raises(PermissionError):
        load_private_config(path, {"key"})
    path.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        load_private_config(link, {"key"})


@pytest.mark.parametrize("data", [[], {"unknown": "value"}, {"key": 123}, {"key": ""}])
def test_invalid_config_values(tmp_path, data):
    path = tmp_path / "config.secret.json"
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    with pytest.raises(ValueError):
        load_private_config(path, {"key"})
