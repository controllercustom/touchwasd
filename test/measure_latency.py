#!/usr/bin/env python3
"""Measure touchWASD key press latency.

Measures two latency components:
  - Firmware processing: WS receive -> HID send (from [TIMING] serial output)
  - End-to-end via evdev: WS send -> HID key press on host (polling active_keys)

Uses EVIOCGKEY (active_keys) instead of the event stream to avoid
OS auto-repeat and stale event buffer issues.

Usage:
  python3 test/measure_latency.py --host 192.168.1.x
  python3 test/measure_latency.py --host 192.168.1.x --samples 50 --key d

Requirements: pyserial, websocket-client, evdev (for HID arrival timing)
"""

import argparse
import os
import queue
import re
import sys
import threading
import time

# Prevent proxy interference with WebSocket connections
for _k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY']:
    os.environ.pop(_k, None)

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

try:
    from websocket import create_connection
except ImportError:
    print("ERROR: websocket-client not installed. Run: pip install websocket-client")
    sys.exit(1)

TIMING_RE = re.compile(rb'\[TIMING\] ws=(\d+) hid=(\d+) fw_us=(\d+)')

# USB HID usage codes -> Linux input event codes (from evdev_hid.py)
HID_TO_LINUX = {
    0x04: 30, 0x1A: 17, 0x16: 31, 0x07: 32,  # a, w, s, d
}
LINUX_KEYS = {'w': 17, 'a': 30, 's': 31, 'd': 32}


def serial_reader(ser, q, stop):
    """Background thread: read Serial lines, queue parsed timing data."""
    while not stop.is_set():
        try:
            line = ser.readline()
        except serial.SerialException:
            break
        if not line:
            continue
        m = TIMING_RE.search(line)
        if m:
            q.put({
                't_host': time.monotonic_ns(),
                'fw_us': int(m.group(3)),
            })


def setup_evdev():
    """Find the ESP32 USB HID keyboard evdev device.

    Returns (device, ecodes_module) or (None, None).
    """
    try:
        import evdev
        from evdev import ecodes
    except ImportError:
        return None, None
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
            if ecodes.EV_KEY not in dev.capabilities():
                dev.close()
                continue
            if 'ESP32' in dev.name:
                return dev, ecodes
            dev.close()
        except (OSError, PermissionError):
            continue
    return None, None


def wait_for_hid_key(dev, expected_linux_code, timeout_s=1.0):
    """Poll active_keys() until the expected Linux keycode is pressed.

    Returns host monotonic ns when the key first appears, or None on timeout.
    Uses EVIOCGKEY (active_keys) — no event buffer, no auto-repeat issues.
    """
    if dev is None:
        return None
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        try:
            keys = dev.active_keys()
        except (OSError, RuntimeError):
            return None
        if expected_linux_code in keys:
            return time.monotonic_ns()
        time.sleep(0.0005)
    return None


def main():
    p = argparse.ArgumentParser(description='Measure touchWASD key press latency')
    p.add_argument('--host', required=True, help='ESP32 hostname or IP address')
    p.add_argument('--serial', default='/dev/ttyUSB0',
                   help='Serial port (default: /dev/ttyUSB0)')
    p.add_argument('--baud', type=int, default=115200,
                   help='Serial baud rate (default: 115200)')
    p.add_argument('--samples', type=int, default=30,
                   help='Number of measurement samples (default: 30)')
    p.add_argument('--key', default='w', choices=['w', 'a', 's', 'd'],
                   help='Key to press (default: w)')
    p.add_argument('--interval', type=float, default=0.3,
                   help='Delay between presses in seconds (default: 0.3)')
    args = p.parse_args()

    expected_linux_key = LINUX_KEYS[args.key]

    # ---- Open serial (DTR/RTS low to avoid resetting the board) ----
    print(f"Serial:  {args.serial} @ {args.baud} baud")
    ser = serial.Serial()
    ser.port = args.serial
    ser.baudrate = args.baud
    ser.timeout = 1
    ser.dtr = False
    ser.rts = False
    ser.open()
    ser.reset_input_buffer()
    time.sleep(0.2)
    ser.reset_input_buffer()
    print("         OK")

    # ---- Connect WebSocket ----
    ws_url = f"ws://{args.host}:81/"
    print(f"WebSocket: {ws_url}")
    ws = create_connection(ws_url, timeout=10)
    print("           OK")

    # ---- Set up evdev HID monitor ----
    dev, ecodes = setup_evdev()
    if dev:
        print(f"USB HID:  {dev.name} at {dev.path}")
    else:
        print("USB HID:  not found (install evdev, check permissions, plug USB)")

    # ---- Start serial reader thread ----
    q = queue.Queue()
    stop = threading.Event()
    reader = threading.Thread(target=serial_reader, args=(ser, q, stop))
    reader.start()

    # ---- Warm up: release all, flush stale data ----
    ws.send('~')
    time.sleep(0.2)
    ser.reset_input_buffer()
    for _ in range(5):
        ws.send(args.key)
        time.sleep(0.1)
        ws.send(f'~{args.key}')
        time.sleep(0.15)
    ser.reset_input_buffer()
    while not q.empty():
        q.get_nowait()
    time.sleep(0.3)

    # ---- Measure ----
    fw_times = []
    hid_times = []
    print(f"\nMeasuring {args.samples}x '{args.key}' press...\n")

    for i in range(args.samples):
        # Drain stale data before this sample
        ser.reset_input_buffer()
        while not q.empty():
            q.get_nowait()

        t_send = time.monotonic_ns()
        ws.send(args.key)

        # Poll active_keys for the expected key
        t_hid_arrival = wait_for_hid_key(dev, expected_linux_key)

        # Read serial timing data
        timing = None
        try:
            timing = q.get(timeout=1.0)
        except queue.Empty:
            pass

        # Release
        ws.send(f'~{args.key}')

        # Record
        if timing is not None:
            fw_times.append(timing['fw_us'])
        if t_hid_arrival is not None:
            hid_us = (t_hid_arrival - t_send) / 1000
            hid_times.append(hid_us)
            hid_str = f"  hid={hid_us:7.0f}us"
        else:
            hid_str = "  (no hid)"

        fw_str = f"fw={timing['fw_us']:3d}us" if timing else "fw=---"
        print(f"  [{i+1:3d}/{args.samples}] {fw_str}{hid_str}")

        time.sleep(args.interval)

    # ---- Cleanup ----
    stop.set()
    reader.join(timeout=2)
    ser.close()
    ws.close()
    if dev:
        dev.close()

    # ---- Report ----
    def stats(label, values, unit='us'):
        if not values:
            return
        values.sort()
        n = len(values)
        mean = sum(values) / n
        median = values[n // 2]
        print(f"\n{label}:")
        print(f"  Samples: {n}")
        print(f"  Mean:    {mean:9.1f} {unit}")
        print(f"  Median:  {median:9.1f} {unit}")
        print(f"  Min:     {min(values):9.1f} {unit}")
        print(f"  Max:     {max(values):9.1f} {unit}")
        if n > 1:
            variance = sum((x - mean) ** 2 for x in values) / (n - 1)
            print(f"  Stdev:   {variance ** 0.5:9.1f} {unit}")

    print("\n" + "=" * 45)
    print("LATENCY RESULTS")
    print("=" * 45)
    stats("Firmware processing (WS recv -> HID send)", fw_times)
    if hid_times:
        stats("End-to-end via evdev (WS send -> HID press on host)", hid_times)
    else:
        print("\nEnd-to-end via evdev: no data")
    print()


if __name__ == '__main__':
    main()
