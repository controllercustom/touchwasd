"""evdev-based USB HID inspection for live touchWASD device tests.

The ESP32-S3 exposes itself as a USB HID keyboard to the host (e.g.
``/dev/input/event5`` named ``Espressif Systems ESP32S3_DEV Keyboard``).
This module lets a test read the actual keystrokes the device emits and
translate them back into the USB HID usage codes used by the firmware and
the protocol tests (see ``test_core.CHAR_TO_HID`` / ``ARROW_MAP``).
"""

evdev = None
ecodes = None
try:
    import evdev  # noqa: F811
    from evdev import ecodes  # noqa: F811
    _EVDEV_AVAILABLE = True
except ImportError:
    _EVDEV_AVAILABLE = False


# USB HID Keyboard/Keypad usage page (0x07) -> Linux input event keycode.
# Linux keycodes are stable (see <linux/input-event-codes.h>).
HID_TO_EVDEV = {
    0x04: 30, 0x05: 48, 0x06: 46, 0x07: 32, 0x08: 18, 0x09: 33,
    0x0A: 34, 0x0B: 35, 0x0C: 23, 0x0D: 36, 0x0E: 37, 0x0F: 38,
    0x10: 50, 0x11: 49, 0x12: 24, 0x13: 25, 0x14: 16, 0x15: 19,
    0x16: 31, 0x17: 20, 0x18: 22, 0x19: 47, 0x1A: 17, 0x1B: 45,
    0x1C: 21, 0x1D: 44,
    0x1E: 2, 0x1F: 3, 0x20: 4, 0x21: 5, 0x22: 6, 0x23: 7,
    0x24: 8, 0x25: 9, 0x26: 10, 0x27: 11,
    0x28: 28, 0x29: 1, 0x2A: 14, 0x2B: 15, 0x2C: 57,
    0x2D: 12, 0x2E: 13, 0x2F: 26, 0x30: 27, 0x31: 43, 0x32: 86,
    0x33: 39, 0x34: 40, 0x35: 41, 0x36: 51, 0x37: 52, 0x38: 53,
    0x39: 58,
    0x3A: 59, 0x3B: 60, 0x3C: 61, 0x3D: 62, 0x3E: 63, 0x3F: 64,
    0x40: 65, 0x41: 66, 0x42: 67, 0x43: 68, 0x44: 69, 0x45: 70,
    0x46: 83, 0x47: 70,
    0x48: 97, 0x49: 54, 0x4A: 100, 0x4B: 126,
    0x4C: 29, 0x4D: 42, 0x4E: 56, 0x4F: 106,
    0x50: 105, 0x51: 108, 0x52: 103, 0x53: 125,
}
EVDEV_TO_HID = {v: k for k, v in HID_TO_EVDEV.items()}

DEFAULT_KEYBOARD_NAME = "ESP32S3_DEV Keyboard"


class HidMonitor:
    """Background reader that tracks currently-pressed HID usage codes.

    The kernel already translates the device's USB HID reports into Linux
    ``EV_KEY`` events; this class maps those back to the HID usage codes
    the firmware thinks it is sending.
    """

    def __init__(self, device):
        self.device = device

    @classmethod
    def find(cls, name_substr=None):
        if not _EVDEV_AVAILABLE:
            return None
        try:
            for path in evdev.list_devices():
                dev = evdev.InputDevice(path)
                # If a specific substring is given, match it exactly.  Otherwise
                # fall back to matching any ESP32 keyboard (covers AtomS3,
                # generic S3 DevKit, etc.).
                if ecodes.EV_KEY not in dev.capabilities():
                    continue
                if name_substr:
                    if name_substr in dev.name:
                        return cls(dev)
                else:
                    if "ESP32" in dev.name:
                        return cls(dev)
        except (OSError, PermissionError):
            return None
        return None

    def get_pressed_hid(self):
        """Currently-pressed HID usage codes, read from the kernel.

        Uses ``InputDevice.active_keys()`` (the EVIOCGKEY bitmap) rather
        than accumulating EV_KEY events: this is race-free and immune to
        the OS auto-repeat stream, and needs no background reader.
        """
        try:
            codes = self.device.active_keys()
        except (OSError, RuntimeError):
            return []
        return sorted(EVDEV_TO_HID[c] for c in codes if c in EVDEV_TO_HID)

    def clear(self):
        # Polling-based monitor keeps no local state; nothing to clear.
        pass

    def close(self):
        try:
            self.device.close()
        except OSError:
            pass


# Module-level cache so the conftest fixture can set it once.
_hid_name_override: str | None = None


def _set_hid_name_override(value: str | None):
    global _hid_name_override
    _hid_name_override = value


def find_keyboard_monitor(name_substr=DEFAULT_KEYBOARD_NAME):
    if not _EVDEV_AVAILABLE:
        return None
    # If the caller didn't pass an explicit substring and a --hid-name override
    # was set via conftest, honour that.  Otherwise fall through to auto-detect
    # (name_substr=None triggers the broad ESP32 keyboard match).
    effective = _hid_name_override if name_substr == DEFAULT_KEYBOARD_NAME else name_substr
    return HidMonitor.find(effective)
