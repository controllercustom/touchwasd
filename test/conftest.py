def pytest_addoption(parser):
    parser.addoption(
        "--host",
        action="store",
        help="AtomS3 hostname or IP (e.g. touchwasd.local) for live device tests",
    )
    parser.addoption(
        "--hid-name",
        action="store",
        default=None,
        help=(
            "Substring to match the USB HID keyboard name in /dev/input/event*. "
            "Default: auto-detect any ESP32 keyboard."
        ),
    )


def pytest_configure(config):
    hid_name = config.getoption("--hid-name")
    from .evdev_hid import _set_hid_name_override
    _set_hid_name_override(hid_name)
