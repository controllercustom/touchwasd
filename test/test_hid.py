"""Live USB HID inspection tests using python3-evdev.

These run against the real device over WebSocket (``--host``) and verify
the actual keystrokes it emits as a USB HID keyboard on the host, read
from ``/dev/input/event*`` via evdev. They are skipped unless:
  * ``--host <ip>`` is supplied, and
  * the ESP32-S3's USB HID keyboard is visible to evdev.

For pure protocol/mock coverage (no hardware) run without ``--host``.
"""

import time

import pytest

from .evdev_hid import HidMonitor, _EVDEV_AVAILABLE
from .test_protocol import (
    LiveTouchWASDDevice,
    _ws_connect,
    _normalize_live_mode,
    char_to_hid,
    ARROW_MAP,
)


@pytest.fixture
def hid_device(request):
    host = request.config.getoption("--host")
    if not host:
        pytest.skip("Live HID test requires --host <device ip>")
    if not _EVDEV_AVAILABLE:
        pytest.skip("python3-evdev not installed")
    dev = LiveTouchWASDDevice(host)
    if not dev.can_inspect:
        pytest.skip("ESP32S3_DEV Keyboard not found via evdev")
    _normalize_live_mode(dev)
    yield dev
    dev.stop()


class TestLiveHid:
    def test_press_w_emits_key(self, hid_device):
        ws = _ws_connect(hid_device)
        ws.recv_text()
        ws.send_text("w")
        time.sleep(0.5)
        keys = hid_device.get_pressed_keys()
        assert char_to_hid("w") in keys
        ws.send_text("~w")
        time.sleep(0.5)
        assert hid_device.get_pressed_keys() == []
        ws.close()

    def test_diagonal_emits_two_keys(self, hid_device):
        ws = _ws_connect(hid_device)
        ws.recv_text()
        ws.send_text("w")
        ws.send_text("d")
        time.sleep(0.5)
        keys = hid_device.get_pressed_keys()
        assert char_to_hid("w") in keys
        assert char_to_hid("d") in keys
        ws.send_text("~")
        time.sleep(0.5)
        assert hid_device.get_pressed_keys() == []
        ws.close()

    def test_arrow_mode_emits_arrow_key(self, hid_device):
        ws = _ws_connect(hid_device)
        ws.recv_text()
        ws.send_text("#MODE:arrows")
        ws.recv_text()
        ws.send_text("w")
        time.sleep(0.5)
        keys = hid_device.get_pressed_keys()
        assert ARROW_MAP["w"] in keys
        assert char_to_hid("w") not in keys
        ws.send_text("~w")
        time.sleep(0.5)
        assert hid_device.get_pressed_keys() == []
        ws.close()

    def test_release_all_clears_hid(self, hid_device):
        ws = _ws_connect(hid_device)
        ws.recv_text()
        ws.send_text("a")
        ws.send_text("s")
        ws.send_text("d")
        time.sleep(0.5)
        assert len(hid_device.get_pressed_keys()) == 3
        ws.send_text("~")
        time.sleep(0.5)
        assert hid_device.get_pressed_keys() == []
        ws.close()

    def test_monitor_reports_hid_not_evdev_codes(self, hid_device):
        # 'd' is HID usage 0x07; the raw evdev code (KEY_D=32) must NOT
        # leak through -- the monitor translates back to HID usage codes.
        ws = _ws_connect(hid_device)
        ws.recv_text()
        ws.send_text("d")
        time.sleep(0.5)
        keys = hid_device.get_pressed_keys()
        assert char_to_hid("d") in keys
        assert 32 not in keys
        ws.send_text("~d")
        time.sleep(0.5)
        ws.close()
