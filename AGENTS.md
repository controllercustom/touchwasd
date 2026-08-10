# AGENTS.md - touchWASD

## Overview
Web-based WASD/Arrow key USB HID keyboard. ESP32-S3 hosts a WebSocket server that serves a circular 8-slice touch overlay. Touch interactions on the web page are translated into USB HID keyboard presses on the host PC.

## Hardware
- **Primary**: M5Stack AtomS3 (`esp32:esp32:m5stack_atoms3`)
- **Alternative**: Generic ESP32-S3 Dev Module (`esp32:esp32:esp32s3`)
- **T-Dongle-S3 / T-Dongle-S3-Plus**: LilyGo (`esp32:esp32:esp32s3` + 16M flash / hwcdc FQBN, see profiles `tdongle_s3` / `tdongle_s3_plus`)

## Key Technical Details
- **USB HID**: Built on the ESP32 core's built-in `USBHIDKeyboard` class (`#include <USB.h>`). Uses a standard keyboard-only report descriptor (no mouse/consumer interfaces). Sends 8-byte boot keyboard reports via `pressRaw()`/`releaseRaw()`.
- **Connectivity**: WiFi via WiFiManager — first boot starts `touchWASD-Config` AP for credential setup.
- **Communication**:
  - Client -> ESP32: WebSocket on port 81 (key presses, mode changes). HTTP on port 80 serves the HTML page only.
  - ESP32 -> Host PC: USB HID Keyboard via custom class wrapping `USBHID`.
- **mDNS**: Default `touchwasd.local`; configurable via "Device hostname" field in the WiFiManager captive portal.
- **OTA**: ArduinoOTA enabled — upload via `espota.py` at `<hostname>.local:3232`. Web OTA at `http://<hostname>.local/update`. Optional password authentication via `#define OTA_PASS` (default commented out) in source (see README).
- **Diagnostics**: Serial monitor at 115200 baud.
- **Display (AtomS3)**: Shows IP, hostname, mode (WASD/Arrows), and client count. Uses M5GFX library.
- **Display (T-Dongle-S3 / Plus)**: Same status on the 160×80 ST7735 via **vendored TFT_eSPI** (`libraries/TFT_eSPI`, version 2.5.43). Auto-detected at compile time with `__has_include(<TFT_eSPI.h>)` **and** `ARDUINO_USB_MODE == 1` (i.e. `USBMode=hwcdc`, which all tdongle profiles select) → defines `T_DONGLE_S3`. The USB-mode guard prevents a stray global TFT_eSPI from enabling the T-Dongle path on AtomS3/generic builds. The vendored library's `User_Setups/Setup47_ST7735.h` is the T-Dongle-S3 config (ST7735 GREENTAB160x80, BGR, pins MOSI=3 SCLK=5 CS=4 DC=2 RST=1, backlight GPIO38 active-low 0=on). Do not add/remove that marker. The Plus is the same board plus `-DT_DONGLE_S3_PLUS` (only used for a boot banner; display/reset identical).
- **Physical reset**: Hold the built-in button 5s (AtomS3 GPIO41 / generic & T-Dongle-S3 BOOT GPIO0) to erase WiFi credentials and reboot into the `touchWASD-Config` captive portal.

## Modes
- **WASD mode** (default): `w`, `a`, `s`, `d` keycodes via `charToHID()` lookup table
- **Arrow mode**: `KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT` (0x52, 0x51, 0x50, 0x4F). These are standard USB HID usage IDs passed directly to `pressRaw()`/`releaseRaw()`. Keep `test/test_core.py`'s `ARROW_MAP` in sync.
- Mode persisted to Preferences (`touchwasd` namespace, `mode` key) and broadcast to all WebSocket clients

## WebSocket Protocol
| Direction | Message | Meaning |
|-----------|---------|---------|
| Client -> Server | `w` `a` `s` `d` | Press single key |
| Client -> Server | `~w` `~a` `~s` `~d` | Release single key |
| Client -> Server | `~` | Release all keys |
| Client -> Server | `#MODE:wasd` | Switch to WASD mode |
| Client -> Server | `#MODE:arrows` | Switch to arrow mode |
| Server -> Client | `#MODE:wasd` / `#MODE:arrows` | Confirm mode sync |

Diagonal presses (NE, SE, SW, NW) send two individual key messages (e.g., `w` then `d`). Reference counting ensures correct release.

## Build Commands

`sketch.yaml` at the project root pins exact core and library versions for reproducible builds.  
Use `--profile <name>` instead of `--fqbn` for pinned builds:

```bash
# AtomS3 (pinned via sketch.yaml)
arduino-cli compile --profile atoms3 .

# Generic ESP32-S3 (pinned via sketch.yaml)
arduino-cli compile --profile esp32s3 .

# LilyGo T-Dongle-S3 (pinned via sketch.yaml; vendored TFT_eSPI from libraries/)
arduino-cli compile --profile tdongle_s3 .

# LilyGo T-Dongle-S3-Plus (same FQBN as base; define T_DONGLE_S3_PLUS for the banner)
arduino-cli compile --profile tdongle_s3_plus . --build-property compiler.cpp.extra_flags=-DT_DONGLE_S3_PLUS

# Serial upload — AtomS3: hold Reset button 2-3s for download mode (LED turns green)
arduino-cli upload -p /dev/ttyACM0 --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .

# Serial upload — Generic ESP32-S3 (port is typically /dev/ttyUSB0 or /dev/ttyACMx)
arduino-cli upload -p /dev/ttyUSB0 --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" .

# Serial upload — T-Dongle-S3 / Plus (native USB CDC, typically /dev/ttyACM0;
# hold BOOT while plugging in to enter download mode)
arduino-cli upload -p /dev/ttyACM0 --profile tdongle_s3 .
arduino-cli upload -p /dev/ttyACM0 --profile tdongle_s3_plus .

# Native OTA upload (arduino-cli 1.5.1+). Pass the device IP (or hostname) directly
# to `-p` with `--protocol network` (without it arduino-cli tries to open the
# address as a serial port). Default OTA port is 3232; ArduinoOTA must be enabled
# in firmware (it is). A disabled OTA password is passed as `--upload-field password=""`.
# Use the device IP when mDNS is unreliable.
arduino-cli compile --profile atoms3 . \
  && arduino-cli upload -p <ip> --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  --upload-field port=3232 --upload-field password="" \
  --protocol network \
  .

# Fallback OTA upload via espota.py (path must match installed esp32 core)
arduino-cli compile --profile atoms3 . --output-dir /tmp/touchwasd-build \
  && python3 ~/.arduino15/packages/esp32/hardware/esp32/3.3.10/tools/espota.py \
  -i <ip> -p 3232 -f /tmp/touchwasd-build/touchwasd.ino.bin -r -d
# If OTA password is enabled, add: -a "<password>"

## Flashing from a different computer (`upload/`)

The T-Dongle-S3 boards are usually flashed from a machine that does NOT build
the firmware. The handoff payload lives in `upload/` (kept trackable via
`.gitignore` exceptions despite the `build/` rule):

- `upload/build/tdongle_s3/` and `upload/build/tdongle_s3_plus/` — precompiled
  binaries (`touchwasd.ino.bin`, `.bootloader.bin`, `.partitions.bin`,
  `.merged.bin`, `boot_app0.bin`).
- `upload/upload.sh` (base) / `upload/upload_plus.sh` (Plus) — install the
  `esp32:esp32` core if missing, then `arduino-cli upload --input-dir`.

Usage on the target machine: `./upload.sh [PORT]` (default `/dev/ttyACM0`).
After changing the sketch you MUST refresh these binaries, e.g.:

```bash
arduino-cli compile --profile tdongle_s3 . --output-dir upload/build/tdongle_s3
arduino-cli compile --profile tdongle_s3_plus . --output-dir upload/build/tdongle_s3_plus \
  --build-property compiler.cpp.extra_flags=-DT_DONGLE_S3_PLUS
cp ~/.arduino15/packages/esp32/hardware/esp32/*/tools/partitions/boot_app0.bin \
  upload/build/tdongle_s3/ upload/build/tdongle_s3_plus/
```

## Latency Optimization

Measured end-to-end latency on ESP32-S3 dev module (50 samples, `test/test_e2e.py`):

| Component | Min | Median | Avg | p99 | Max |
|-----------|-----|--------|-----|-----|-----|
| Firmware processing (WS recv → HID send) | **10 µs** | **11 µs** | **11 µs** | **20 µs** | **20 µs** |
| End-to-end (WS send → HID on host via evdev) | **3.4 ms** | **3.8 ms** | **4.9 ms** | **15.8 ms** | **15.8 ms** |

The default CI gate threshold is **p99 < 20 ms** for end-to-end latency (configurable via `--e2e-threshold`).

### Optimizations applied
1. **CPU frequency**: `setCpuFrequencyMhz(240)` in `setup()` — ensures max clock rate
2. **Main loop reorder**: `webSocket.loop()` called first, before `server.handleClient()` and `ArduinoOTA.handle()` — minimizes polling delay for WS messages
3. **WiFi modem sleep disabled**: `esp_wifi_set_ps(WIFI_PS_NONE)` after WiFi connects — prevents modem sleep from adding 50-200ms of latency. This was the dominant bottleneck (ping dropped from ~130ms to ~5ms).

### Measurement

Two tools measure latency:

- **`test/test_e2e.py`** (standalone, pytest-free) — sends key presses over WebSocket, observes HID arrival via `select.select()` on the evdev fd (event-driven), and optionally reads `[TIMING]` markers from the UART for firmware processing split. Passes/fails on a configurable p99 threshold (default 20ms).
  ```bash
  python3 test/test_e2e.py --host <ip> --serial /dev/ttyUSB0 --samples 50
  ```

- **`test/measure_latency.py`** (standalone) — measures both firmware processing time (via Serial `[TIMING]` output) and end-to-end HID arrival (via `evdev.active_keys()`, EVIOCGKEY). More detailed diagnostic output; no pass/fail gate.
  ```bash
  python3 test/measure_latency.py --host <ip> --samples 50
  ```

> **`[TIMING]` output is opt-in**: compile with `-DTIMING_OUTPUT` (e.g. `--build-property build.extra_flags=-DTIMING_OUTPUT`) to enable the firmware processing time marker. Without it, no UART timing data is emitted on the hot path.

## Key Design Decisions (from ikeys)
- **Reference counting**: `keyRefCount[256]` enables multi-client support. Two clients pressing `w` simultaneously increment the ref count; one releasing does not release the key.
- **Reset on disconnect**: `resetState()` clears all pressed keys when client count changes (connect/disconnect).
- **WDT**: After 5s of WebSocket inactivity, held keys are released (only acts when `keyRefCount` entries are non-zero). Tracked locally — no library API needed.
- **USB setup**: Handled by the built-in core — `keyboard.begin()` registers a keyboard-only HID report descriptor via TinyUSB and calls `HID.begin()`.

## Web UI
- Embedded as a C++ raw string literal in `webpage.h` (`R"rawliteral(...)rawliteral"`)
- SVG-based 8-segment circle (outer r=96, inner r=28) rendered using `<path>` arcs
- Pointer Events API for touch: `pointerdown`/`pointermove`/`pointerup`/`pointercancel`
- Slide-typing across slices via `document.elementFromPoint()` in `pointermove`
- Settings panel (cog button): "USB output" toggle (WASD vs Arrows), 4 sizes, 7 positions, and Appearance toggle ("Clean" arrows-only or "Labels" with WASD text + directional hints)
- Client-side persistence via `localStorage`: size (`tw-sz`), position (`tw-ps`), appearance look (`tw-lk`)
- Landscape layout: on screens ≥769px wide, settings sections arrange side-by-side in a flex row. Mobile (≤768px) stacks vertically. Rotating a phone auto-switches based on viewport width.
- Gear button auto-relocates to the opposite corner when the circle is at any edge position (e.g. top→bottom-left, bottom-right→top-left, etc.) to avoid overlap

## Tests

Python 3 test suite at `test/`. Tests both core logic and wire protocol:

```bash
# Mock device tests (no hardware needed)
python3 -m pytest test/ -v

# Live device tests (requires AtomS3 on the network, USB plugged into host for HID inspection)
python3 -m pytest test/ --host 192.168.1.xxx -v
```

The `--host` flag switches `MockTouchWASDDevice` for a `LiveTouchWASDDevice` connection to the real device; without it the full suite runs against the in-process mock. The optional `--hid-name <substring>` flag overrides auto-detection of the USB HID keyboard name (e.g., `--hid-name "ESP32S3_DEV"`).

With `python3-evdev` installed and the device's USB HID keyboard visible to the host (`/dev/input/event*`, user must be in the **input** group on Ubuntu 24.04+), the live tests also assert the **actual USB HID keystrokes** the device emits, read from `EVIOCGKEY` via evdev — see `test/test_hid.py`. The keyboard name is auto-detected by matching `"ESP32"` or `"Espressif"` in the device name (covers AtomS3 which reports as `"M5STACK_ATOMS3"`, generic S3 DevKit, etc.). Without evdev or HID access, those assertions are skipped and only protocol-level checks run.

### `test/test_core.py` — Unit tests (stdlib only, no dependencies)
- `charToHID()` lookup table validation against every ASCII character
- Key state management: press/release lifecycle, 6-key limit, swap-removal
- Reference counting: multi-client, overflow cap at 255
- Mode mapping: WASD vs Arrow key translation
- HID report format: 8-byte report structure

### `test/test_protocol.py` — Integration tests (requires `websocket-client`)
- `MockTouchWASDDevice`: simulated ESP32 with WS+HTTP servers
- WebSocket handshake, key press/release, diagonal, release-all (`~`)
- Mode switch round-trip (`#MODE:wasd` / `#MODE:arrows`)
- Two-client reference counting over real WS connections (skipped on live device — internal refcount state not accessible)
- Disconnect resets state, new client receives mode sync
- HTTP root page serving

### `test/test_hid.py` — Live USB HID inspection (requires `--host` + `python3-evdev`)
- Reads the device's real keystrokes via evdev (`/dev/input/event*`)
- Press/release round-trip, diagonal two-key, arrow-mode mapping, release-all
- Verifies the monitor reports HID usage codes (not raw evdev codes)

### `test/test_e2e.py` — Latency measurement (standalone, no pytest)
- Sends key presses over WebSocket, observes HID arrival via evdev `select.select()`
- Measures end-to-end latency (WS send → USB HID on host) with statistical report
- Optional `--serial` flag reads `[TIMING]` markers for firmware processing time split
- Configurable pass/fail threshold (default 20ms p99)
- Usage: `python3 test/test_e2e.py --host <ip> [--serial /dev/ttyUSB0] [--samples 50]`

## Calibration Notes
- The SVG uses a 200x200 viewBox. Outer circle r=96, inner cutout r=28.
- The top slice (W) is centered at 0° (straight up), spanning from 337.5° to 22.5° (45° arc). All other slices follow clockwise.
- The `describeArc()` function generates SVG path data for arc segments. It handles the wrap-around for the top slice correctly.