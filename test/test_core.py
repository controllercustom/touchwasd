import pytest

KEY_UP    = 0x52
KEY_DOWN  = 0x51
KEY_LEFT  = 0x50
KEY_RIGHT = 0x4F

CHAR_TO_HID = bytes([
    0,0,0,0,0,0,0,0, 0x2A,0x2B,0x28,0,0,0x28,0,0,
    0,0,0,0,0,0,0,0, 0,0,0,0x29,0,0,0,0,
    0x2C,0x1E,0x34,0x20, 0x21,0x22,0x24,0x34,
    0x26,0x27,0x25,0x2E, 0x36,0x2D,0x37,0x38,
    0x27,0x1E,0x1F,0x20, 0x21,0x22,0x23,0x24,
    0x25,0x26,0x33,0x33, 0x36,0x2E,0x37,0x38,
    0x1F,0x04,0x05,0x06, 0x07,0x08,0x09,0x0A,
    0x0B,0x0C,0x0D,0x0E, 0x0F,0x10,0x11,0x12,
    0x13,0x14,0x15,0x16, 0x17,0x18,0x19,0x1A,
    0x1B,0x1C,0x1D,0x2F, 0x31,0x30,0x23,0x2D,
    0x35,0x04,0x05,0x06, 0x07,0x08,0x09,0x0A,
    0x0B,0x0C,0x0D,0x0E, 0x0F,0x10,0x11,0x12,
    0x13,0x14,0x15,0x16, 0x17,0x18,0x19,0x1A,
    0x1B,0x1C,0x1D,0x2F, 0x31,0x02,0x35,0
])


def char_to_hid(c: str) -> int:
    v = ord(c)
    if v > 127:
        return 0
    return CHAR_TO_HID[v]


ARROW_MAP = {'w': KEY_UP, 'a': KEY_LEFT, 's': KEY_DOWN, 'd': KEY_RIGHT}


class KeyState:
    def __init__(self):
        self.refcount = [0] * 256
        self.pressed = [0] * 6
        self.count = 0
        self.last_report = (0, 0, 0, 0, 0, 0, 0, 0)

    def _send_report(self):
        r = [0, 0]
        r.extend(self.pressed[:self.count])
        r.extend([0] * (6 - self.count))
        self.last_report = tuple(r)

    def press_keycode(self, kc: int):
        if self.refcount[kc] == 0:
            for i in range(self.count):
                if self.pressed[i] == kc:
                    return
            if self.count < 6:
                self.pressed[self.count] = kc
                self.count += 1
        if self.refcount[kc] < 255:
            self.refcount[kc] += 1
        self._send_report()

    def release_keycode(self, kc: int):
        if self.refcount[kc] > 0:
            self.refcount[kc] -= 1
        if self.refcount[kc] > 0:
            return
        for i in range(self.count):
            if self.pressed[i] == kc:
                self.count -= 1
                self.pressed[i] = self.pressed[self.count]
                self.pressed[self.count] = 0
                break
        self._send_report()

    def reset(self):
        self.refcount = [0] * 256
        self.pressed = [0] * 6
        self.count = 0
        self._send_report()

    def press_char(self, c: str, mode: str = 'wasd'):
        if mode == 'arrows':
            kc = ARROW_MAP.get(c, 0)
        else:
            kc = char_to_hid(c)
        if kc:
            self.press_keycode(kc)

    def release_char(self, c: str, mode: str = 'wasd'):
        if mode == 'arrows':
            kc = ARROW_MAP.get(c, 0)
        else:
            kc = char_to_hid(c)
        if kc:
            self.release_keycode(kc)


class TestCharToHID:
    def test_lowercase_letter_a(self):
        assert char_to_hid('a') == 0x04

    def test_lowercase_letter_d(self):
        assert char_to_hid('d') == 0x07

    def test_lowercase_letter_s(self):
        assert char_to_hid('s') == 0x16

    def test_lowercase_letter_w(self):
        assert char_to_hid('w') == 0x1A

    def test_lowercase_letter_z(self):
        assert char_to_hid('z') == 0x1D

    def test_uppercase_same_hid_as_lowercase(self):
        assert char_to_hid('A') == char_to_hid('a')
        assert char_to_hid('Z') == char_to_hid('z')

    def test_digit_keys(self):
        assert char_to_hid('1') == 0x1E
        assert char_to_hid('2') == 0x1F
        assert char_to_hid('0') == 0x27

    def test_space(self):
        assert char_to_hid(' ') == 0x2C

    def test_enter(self):
        assert char_to_hid('\n') == 0x28
        assert char_to_hid('\r') == 0x28

    def test_tab(self):
        assert char_to_hid('\t') == 0x2B

    def test_escape(self):
        assert char_to_hid('\x1b') == 0x29

    def test_backspace(self):
        assert char_to_hid('\b') == 0x2A

    def test_punctuation(self):
        assert char_to_hid('.') == 0x37
        assert char_to_hid(',') == 0x36
        assert char_to_hid('!') == 0x1E

    def test_out_of_range_returns_zero(self):
        assert char_to_hid('\x80') == 0
        assert char_to_hid('\xff') == 0

    def test_control_chars_map_to_zero(self):
        for i in range(0x00, 0x08):
            assert char_to_hid(chr(i)) == 0, f"char 0x{i:02X} should map to 0"


class TestKeyStatePressRelease:
    def test_press_single_key(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        assert ks.count == 1
        assert ks.pressed[0] == 0x04
        assert ks.refcount[0x04] == 1

    def test_release_single_key(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.release_keycode(0x04)
        assert ks.count == 0
        assert ks.refcount[0x04] == 0

    def test_press_release_cycle(self):
        ks = KeyState()
        for _ in range(3):
            ks.press_keycode(0x04)
            assert ks.count == 1
            assert ks.refcount[0x04] == 1
            ks.release_keycode(0x04)
            assert ks.count == 0
            assert ks.refcount[0x04] == 0

    def test_press_sends_report_with_keycode(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        assert ks.last_report[2] == 0x04
        assert ks.last_report[0] == 0
        assert ks.last_report[1] == 0

    def test_release_sends_empty_report(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.release_keycode(0x04)
        assert ks.last_report == (0, 0, 0, 0, 0, 0, 0, 0)


class TestRefCounting:
    def test_two_clients_press_same_key(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x04)
        assert ks.refcount[0x04] == 2
        assert ks.count == 1

    def test_one_client_release_does_not_release(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x04)
        ks.release_keycode(0x04)
        assert ks.refcount[0x04] == 1
        assert ks.count == 1

    def test_both_clients_release(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x04)
        ks.release_keycode(0x04)
        ks.release_keycode(0x04)
        assert ks.refcount[0x04] == 0
        assert ks.count == 0

    def test_refcount_does_not_overflow(self):
        ks = KeyState()
        for _ in range(300):
            ks.press_keycode(0x04)
        assert ks.refcount[0x04] == 255

    def test_refcount_wrap_release(self):
        ks = KeyState()
        for _ in range(300):
            ks.press_keycode(0x04)
        assert ks.refcount[0x04] == 255
        for _ in range(300):
            ks.release_keycode(0x04)
        assert ks.refcount[0x04] == 0
        assert ks.count == 0


class TestMultiKey:
    def test_two_keys(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x07)
        assert ks.count == 2
        assert 0x04 in ks.pressed[:ks.count]
        assert 0x07 in ks.pressed[:ks.count]

    def test_three_keys_then_release_middle(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x07)
        ks.press_keycode(0x16)
        ks.release_keycode(0x07)
        assert ks.count == 2
        assert 0x07 not in ks.pressed[:ks.count]
        assert 0x04 in ks.pressed[:ks.count]
        assert 0x16 in ks.pressed[:ks.count]

    def test_max_six_keys(self):
        ks = KeyState()
        for i in range(6):
            ks.press_keycode(0x04 + i)
        assert ks.count == 6

    def test_seventh_key_not_added_to_pressed(self):
        ks = KeyState()
        for i in range(6):
            ks.press_keycode(0x04 + i)
        ks.press_keycode(0x20)
        assert ks.count == 6
        for i in range(6):
            assert ks.pressed[i] == 0x04 + i

    def test_seventh_key_refcount_still_increments(self):
        ks = KeyState()
        for i in range(6):
            ks.press_keycode(0x04 + i)
        ks.press_keycode(0x20)
        assert ks.refcount[0x20] == 1

    def test_diagonal_press_two_keys(self):
        ks = KeyState()
        ks.press_char('w')
        ks.press_char('d')
        assert ks.count == 2
        assert char_to_hid('w') in ks.pressed[:ks.count]
        assert char_to_hid('d') in ks.pressed[:ks.count]

    def test_diagonal_release(self):
        ks = KeyState()
        ks.press_char('w')
        ks.press_char('d')
        ks.release_char('w')
        ks.release_char('d')
        assert ks.count == 0


class TestKeyArrayManagement:
    def test_swap_removal_maintains_invariants(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x07)
        ks.press_keycode(0x16)
        ks.press_keycode(0x1A)
        ks.release_keycode(0x04)
        assert ks.count == 3
        for kc in [0x07, 0x16, 0x1A]:
            assert kc in ks.pressed[:ks.count]
        assert 0x04 not in ks.pressed[:ks.count]
        assert ks.pressed[ks.count] == 0

    def test_release_key_not_pressed(self):
        ks = KeyState()
        ks.release_keycode(0x99)
        assert ks.count == 0

    def test_press_already_pressed_key_no_dup(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x04)
        ks.release_keycode(0x04)
        assert ks.count == 1
        ks.release_keycode(0x04)
        assert ks.count == 0


class TestReset:
    def test_reset_clears_all(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x07)
        ks.press_keycode(0x16)
        ks.reset()
        assert ks.count == 0
        assert all(v == 0 for v in ks.refcount)
        assert all(v == 0 for v in ks.pressed)

    def test_reset_sends_empty_report(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.reset()
        assert ks.last_report == (0, 0, 0, 0, 0, 0, 0, 0)

    def test_after_reset_keys_can_be_pressed_again(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.reset()
        ks.press_keycode(0x04)
        assert ks.count == 1
        assert ks.refcount[0x04] == 1


class TestModeMapping:
    def test_wasd_mode_presses_w(self):
        ks = KeyState()
        ks.press_char('w', mode='wasd')
        assert char_to_hid('w') in ks.pressed[:ks.count]

    def test_arrow_mode_presses_up(self):
        ks = KeyState()
        ks.press_char('w', mode='arrows')
        assert KEY_UP in ks.pressed[:ks.count]

    def test_arrow_mode_a_maps_to_left(self):
        ks = KeyState()
        ks.press_char('a', mode='arrows')
        assert KEY_LEFT in ks.pressed[:ks.count]

    def test_arrow_mode_s_maps_to_down(self):
        ks = KeyState()
        ks.press_char('s', mode='arrows')
        assert KEY_DOWN in ks.pressed[:ks.count]

    def test_arrow_mode_d_maps_to_right(self):
        ks = KeyState()
        ks.press_char('d', mode='arrows')
        assert KEY_RIGHT in ks.pressed[:ks.count]

    def test_arrow_mode_release_up(self):
        ks = KeyState()
        ks.press_char('w', mode='arrows')
        ks.release_char('w', mode='arrows')
        assert ks.count == 0

    def test_mode_switch_clears_state(self):
        ks = KeyState()
        ks.press_char('w')
        assert ks.count == 1
        ks.reset()
        assert ks.count == 0


class TestReportFormat:
    def test_report_format_matches_hid_keyboard(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        ks.press_keycode(0x07)
        r = ks.last_report
        assert len(r) == 8
        assert r[0] == 0
        assert r[1] == 0
        assert 0x04 in r[2:8]
        assert 0x07 in r[2:8]
        assert all(k == 0 or isinstance(k, int) for k in r)

    def test_report_has_no_garbage(self):
        ks = KeyState()
        ks.press_keycode(0x04)
        r = ks.last_report
        non_zero_keys = [k for k in r[2:] if k != 0]
        assert len(non_zero_keys) == 1
        assert non_zero_keys[0] == 0x04
