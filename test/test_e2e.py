#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 controllercustom@myyahoo.com
"""
End-to-end latency test for touchWASD.

Connects to the ESP32-S3 over WebSocket, sends key presses,
and measures the time until corresponding USB HID events arrive
via evdev on the host.

Also reads [TIMING] markers from the UART (--serial) to measure
firmware processing time separately.

Usage:
  python3 test/test_e2e.py --host 192.168.1.x
  python3 test/test_e2e.py --host 192.168.1.x --serial /dev/ttyUSB0 --samples 50
  python3 test/test_e2e.py --list
"""

import argparse
import re
import select
import statistics
import sys
import time

from evdev import InputDevice, ecodes, list_devices
import websocket

try:
    import serial as _serial
except ImportError:
    _serial = None

HID_KEY_MAP = {
    'w': 17,
    'a': 30,
    's': 31,
    'd': 32,
}

TIMING_RE = re.compile(rb'\[TIMING\] ws=\d+ hid=\d+ fw_us=(\d+)')

CMD_TIMEOUT_S = 2.0


def find_evdev():
    fallback = None
    for path in list_devices():
        try:
            dev = InputDevice(path)
            if ecodes.EV_KEY not in dev.capabilities():
                dev.close()
                continue
            if 'ESP32' not in dev.name:
                dev.close()
                continue
            if 'Keyboard' in dev.name:
                return dev, path
            if fallback is None:
                fallback = (dev, path)
            else:
                dev.close()
        except (OSError, PermissionError):
            continue
    if fallback:
        return fallback
    return None, None


def find_uart(pattern='/dev/ttyUSB*'):
    import glob
    ports = sorted(glob.glob(pattern))
    return ports[0] if ports else None


def flush_events(dev):
    while True:
        r, _, _ = select.select([dev.fd], [], [], 0)
        if not r:
            break
        try:
            dev.read()
        except OSError:
            break


def wait_for_key_event(dev, code, value=1, timeout=CMD_TIMEOUT_S):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        r, _, _ = select.select([dev.fd], [], [], 0.010)
        if r:
            try:
                events = dev.read()
            except OSError:
                return timeout
            for event in events:
                if event.type == ecodes.EV_KEY and event.code == code and event.value == value:
                    return time.monotonic() - start
    return timeout


def read_timing_serial(ser, timeout=0.5):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        line = ser.readline()
        if not line:
            continue
        m = TIMING_RE.search(line)
        if m:
            return int(m.group(1))
    return None


def test_key_latency(host, ws_port, dev, key, linux_code, num_samples, ser=None):
    ws_url = f'ws://{host}:{ws_port}/'
    ws = websocket.create_connection(ws_url, timeout=10)
    ws.recv()

    for _ in range(5):
        ws.send(key)
        wait_for_key_event(dev, linux_code, 1)
        ws.send(f'~{key}')
        wait_for_key_event(dev, linux_code, 0)
        time.sleep(0.02)

    e2e_latencies = []
    fw_times = []

    for i in range(num_samples):
        flush_events(dev)

        t0 = time.monotonic()
        ws.send(key)

        dt = wait_for_key_event(dev, linux_code, 1)
        if dt < CMD_TIMEOUT_S:
            e2e_latencies.append(dt * 1000)
        else:
            break

        if ser:
            fw = read_timing_serial(ser)
            if fw is not None:
                fw_times.append(fw)

        ws.send(f'~{key}')
        wait_for_key_event(dev, linux_code, 0)
        time.sleep(0.05)

    ws.close()
    return e2e_latencies, fw_times


def report(name, values, unit='ms'):
    if not values:
        print(f'  {name}: NO DATA')
        return None
    values.sort()
    n = len(values)
    avg = statistics.mean(values)
    med = statistics.median(values)
    p99 = values[int(n * 0.99)]
    mx = max(values)
    mn = min(values)
    jitter = statistics.stdev(values) if n > 1 else 0
    print(f'  {name}:')
    print(f'    samples={n}  min={mn:.3f}{unit}  max={mx:.3f}{unit}  avg={avg:.3f}{unit}')
    print(f'    median={med:.3f}{unit}  p99={p99:.3f}{unit}  jitter(σ)={jitter:.3f}{unit}')
    return {'min': mn, 'max': mx, 'avg': avg, 'median': med, 'p99': p99, 'jitter': jitter, 'n': n}


def main():
    parser = argparse.ArgumentParser(description='touchWASD E2E Latency Test')
    parser.add_argument('--host', help='ESP32 hostname or IP address')
    parser.add_argument('--ws-port', type=int, default=81, help='WebSocket port (default: 81)')
    parser.add_argument('--serial', help='UART port (e.g. /dev/ttyUSB0). Enables firmware timing split.')
    parser.add_argument('--baud', type=int, default=115200, help='UART baud rate (default: 115200)')
    parser.add_argument('--samples', type=int, default=50, help='Number of samples (default: 50)')
    parser.add_argument('--key', default='w', choices=['w', 'a', 's', 'd'], help='Key to test (default: w)')
    parser.add_argument('--list', action='store_true', help='List available input devices')
    parser.add_argument('--e2e-threshold', type=float, default=20.0,
                        help='E2E p99 threshold in ms (default: 20)')
    args = parser.parse_args()

    if args.list:
        print('Input devices:')
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except (OSError, PermissionError):
                continue
            tags = []
            if 'ESP32' in dev.name and ecodes.EV_KEY in dev.capabilities():
                tags.append(' *** ESP32 keyboard (touchWASD) ***')
            print(f'  {path}  {dev.name}{"".join(tags)}')
            dev.close()
        return

    if not args.host:
        print('ERROR: --host is required (or use --list to discover devices)')
        sys.exit(1)

    linux_code = HID_KEY_MAP.get(args.key)
    if linux_code is None:
        print(f'ERROR: unknown key {args.key!r}')
        sys.exit(1)

    print(f'touchWASD E2E Latency Test')
    print(f'  Key:           {args.key}  (linux evdev code {linux_code})')
    print(f'  WebSocket:     ws://{args.host}:{args.ws_port}/')
    print(f'  Samples:       {args.samples}')

    evdev_dev, evdev_path = find_evdev()
    if not evdev_dev:
        print('ERROR: ESP32 USB HID keyboard not found via evdev.')
        print('  Is the ESP32-S3 USB plugged in? Are you in the input group?')
        print('  Use --list to see available devices.')
        sys.exit(1)
    print(f'  evdev device:  {evdev_path}  ({evdev_dev.name})')

    ser = None
    if args.serial:
        if _serial is None:
            print('ERROR: pyserial not installed (needed for --serial).')
            print('  Run: pip install pyserial')
            sys.exit(1)
        ser = _serial.Serial(args.serial, args.baud, timeout=1)
        ser.dtr = False
        ser.rts = False

        evdev_dev.close()
        time.sleep(2)
        evdev_dev, evdev_path = find_evdev()
        if not evdev_dev:
            print('ERROR: ESP32 keyboard lost after UART open (board reset?).')
            print('  Try without --serial.')
            sys.exit(1)

        ser.reset_input_buffer()
        print(f'  Serial:        {args.serial} @ {args.baud} baud')
    else:
        uart_port = find_uart()
        if uart_port:
            print(f'  Serial:        {uart_port} (auto-detected, pass --serial to enable timing split)')
        else:
            print(f'  Serial:        not available')

    print()

    e2e_latencies, fw_times = test_key_latency(
        args.host, args.ws_port, evdev_dev, args.key, linux_code,
        args.samples, ser=ser,
    )

    print('\n=== End-to-end Latency (WebSocket -> USB HID) ===')
    e2e_stats = report('E2E', e2e_latencies, 'ms')

    print('\n=== Firmware Processing ([TIMING] from Serial) ===')
    report('Firmware', fw_times, 'us')

    print('\n' + '=' * 50)
    print('SUMMARY')
    print('=' * 50)
    if e2e_stats:
        worst_p99 = e2e_stats['p99']
        print(f'  End-to-end p99:      {worst_p99:.3f}ms')
        print(f'  Threshold:           <{args.e2e_threshold}ms p99')
        passed = worst_p99 < args.e2e_threshold
        print(f'  RESULT:              {"PASS" if passed else "FAIL"}')
    else:
        print('  No end-to-end data collected')
        passed = False

    evdev_dev.close()
    if ser:
        ser.close()

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
