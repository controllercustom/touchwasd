# AGENTS.md - touchWASD

## Overview
Web-based WASD/Arrow key USB HID keyboard. ESP32-S3 hosts a WebSocket server that serves a circular 8-slice touch overlay. Touch interactions on the web page are translated into USB HID keyboard presses on the host PC.

## Hardware
- **Primary**: M5Stack AtomS3 (`esp32:esp32:m5stack_atoms3`)
- **Alternative**: Generic ESP32-S3 Dev Module (`esp32:esp32:esp32s3`)

## Key Technical Details
- **USB HID**: Built on the ESP32 core's built-in `USBHIDKeyboard` class (`#include <USB.h>`). Uses a standard keyboard-only report descriptor (no mouse/consumer interfaces). Sends 8-byte boot keyboard reports via `pressRaw()`/`releaseRaw()`.
- **Connectivity**: WiFi via WiFiManager — first boot starts `touchWASD-Config` AP for credential setup.
- **Communication**:
  - Client -> ESP32: WebSocket on port 81 (key presses, mode changes). HTTP on port 80 serves the HTML page only.
  - ESP32 -> Host PC: USB HID Keyboard via custom class wrapping `USBHID`.
- **mDNS**: Default `touchwasd.local`; configurable via "Device hostname" field in the WiFiManager captive portal.
- **OTA**: ArduinoOTA enabled — upload via `espota.py` at `<hostname>.local:3232`. Web OTA at `http://<hostname>.local/update`. Optional password authentication via `#define OTA_PASS` (default commented out) in source (see README).
- **Diagnostics**: Serial monitor at 115200 baud.
- **Display (AtomS3 only)**: Shows IP, hostname, mode (WASD/Arrows), and client count. Uses M5GFX library.
- **Physical reset**: Hold the built-in button 5s (AtomS3 GPIO41 / generic BOOT GPIO0) to erase WiFi credentials and reboot into the `touchWASD-Config` captive portal.

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
```bash
# AtomS3
arduino-cli compile --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .

# Generic ESP32-S3
arduino-cli compile --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" .

# Lilygo T-Dongle-S3 (ESP32-S3, 16MB flash, ST7735 160x80 SPI display, no PSRAM)
# Display driver: Adafruit ST7735 + Adafruit GFX (installed via arduino-cli lib install).
# Board is selected via -DARDUINO_T_DONGLE_S3 (no dedicated core FQBN exists; uses
# the esp32s3 dev module). The extra -DWEBSOCKETS_NETWORK_TYPE=4 and -DESP32
# defines work around Adafruit_BusIO / WebSockets include-order issues on core 3.3.x.
# Display pins: DC=2, CS=4, MOSI=3, SCK=5, RST=1, Backlight=38 (active-low).
# Button (BOOT) is GPIO0 — same as the generic RESET_BUTTON_PIN.
TDONGLE_FQBN="esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,PartitionScheme=app3M_fat9M_16MB,PSRAM=disabled,FlashSize=16M,FlashMode=qio"
TDONGLE_FLAGS='build.extra_flags=-DARDUINO_T_DONGLE_S3 -DWEBSOCKETS_NETWORK_TYPE=4 -DESP32'
arduino-cli compile --clean --fqbn "$TDONGLE_FQBN" --build-property "$TDONGLE_FLAGS" --output-dir /tmp/tw-dongle .
# Serial upload — board must be in download mode (hold BOOT/GPIO0 while plugging in,
# or the uploader's "Hard resetting via RTS pin" will leave it there; release BOOT
# and replug to run the sketch normally).
arduino-cli upload -p /dev/ttyACM0 --fqbn "$TDONGLE_FQBN" --input-dir /tmp/tw-dongle .

# Serial upload — AtomS3: hold Reset button 2-3s for download mode (LED turns green)
arduino-cli upload -p /dev/ttyACM0 --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .

# Serial upload — Generic ESP32-S3 (port is typically /dev/ttyUSB0 or /dev/ttyACMx)
arduino-cli upload -p /dev/ttyUSB0 --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" .

# Native OTA upload (arduino-cli 1.5.1+). Pass the device IP (or hostname) directly
# to `-p`; arduino-cli recognizes an IP as a network/OTA port automatically — do NOT
# add `-l network` (that fails with "port not found: <ip> network"). Default OTA port
# is 3232; ArduinoOTA must be enabled in firmware (it is). A disabled OTA password is
# passed as `--upload-field password=""`. Use the device IP when mDNS is unreliable.
arduino-cli compile --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" . \
  && arduino-cli upload -p <ip> --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  --upload-field port=3232 --upload-field password="" \
  .

# Fallback OTA upload via espota.py (path version 3.3.8 must match installed esp32 core)
arduino-cli compile --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" . --output-dir /tmp/touchwasd-build \
  && python3 ~/.arduino15/packages/esp32/hardware/esp32/3.3.8/tools/espota.py \
  -i <ip> -p 3232 -f /tmp/touchwasd-build/touchwasd.ino.bin -r -d
# If OTA password is enabled, add: -a "<password>"

## Latency Optimization

Measured end-to-end latency on ESP32-S3 dev module (50-sample median):

| Component | Time |
|-----------|------|
| Firmware processing (WS recv → HID send) | **10 µs** (mean) |
| End-to-end WS send → HID on host (evdev) | **4.5 ms** (median), **3.4 ms** (min) |

### Optimizations applied
1. **CPU frequency**: `setCpuFrequencyMhz(240)` in `setup()` — ensures max clock rate
2. **Main loop reorder**: `webSocket.loop()` called first, before `server.handleClient()` and `ArduinoOTA.handle()` — minimizes polling delay for WS messages
3. **WiFi modem sleep disabled**: `esp_wifi_set_ps(WIFI_PS_NONE)` after WiFi connects — prevents modem sleep from adding 50-200ms of latency. This was the dominant bottleneck (ping dropped from ~130ms to ~5ms).

### Measurement
The `test/measure_latency.py` script measures both firmware processing time (via Serial `[TIMING]` output) and end-to-end HID arrival (via `evdev.active_keys()`, EVIOCGKEY). Run:
```bash
python3 test/measure_latency.py --host <ip> --samples 50
```

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
- Settings panel: cog button opens mode toggle (WASD vs Arrows), 4 sizes (sm/md/lg/xl), and 7 positions (center/top/bottom/topleft/topright/bottomleft/bottomright)
- Size and position persisted client-side via `localStorage` (`tw-sz`, `tw-ps`)
- Gear button auto-relocates to bottom-left when circle is at top-right position to avoid overlap

## Tests

Python 3 test suite at `test/`. Tests both core logic and wire protocol:

```bash
# Mock device tests (no hardware needed)
python3 -m pytest test/ -v

# Live device tests (requires AtomS3 on the network, USB plugged into host for HID inspection)
python3 -m pytest test/ --host 192.168.1.xxx -v
```

The `--host` flag switches `MockTouchWASDDevice` for a `LiveTouchWASDDevice` connection to the real device; without it the full suite runs against the in-process mock. The optional `--hid-name <substring>` flag overrides auto-detection of the USB HID keyboard name (e.g., `--hid-name "ESP32S3_DEV"`).

With `python3-evdev` installed and the device's USB HID keyboard visible to the host (`/dev/input/event*`, user must be in the **input** group on Ubuntu 24.04+), the live tests also assert the **actual USB HID keystrokes** the device emits, read from `EVIOCGKEY` via evdev — see `test/test_hid.py`. The keyboard name is auto-detected by matching any ESP32 keyboard device (AtomS3, generic S3 DevKit, T-Dongle-S3, etc.). Without evdev or HID access, those assertions are skipped and only protocol-level checks run.

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

## Calibration Notes
- The SVG uses a 200x200 viewBox. Outer circle r=96, inner cutout r=28.
- The top slice (W) is centered at 0° (straight up), spanning from 337.5° to 22.5° (45° arc). All other slices follow clockwise.
- The `describeArc()` function generates SVG path data for arc segments. It handles the wrap-around for the top slice correctly.