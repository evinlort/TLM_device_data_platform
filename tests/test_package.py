import tlm_device_data_platform


def test_installed_package_is_importable() -> None:
    assert tlm_device_data_platform.__name__ == "tlm_device_data_platform"
