# AGENTS.md - touchWASD

## Overview
Web-based WASD/Arrow key USB HID keyboard. ESP32-S3 hosts a WebSocket server that serves a circular 8-slice touch overlay. Touch interactions on the web page are translated into USB HID keyboard presses on the host PC.

## Hardware
- **Primary**: M5Stack AtomS3 (`esp32:esp32:m5stack_atoms3`)
- **Alternative**: Generic ESP32-S3 Dev Module (`esp32:esp32:esp32s3`)

## Key Technical Details
- **USB HID**: Built on the `ESP32USBHID` library. Its descriptor is a composite Keyboard (ID1) + Mouse (ID2) + Consumer (ID3), but touchWASD only sends keyboard reports (single Report ID 1). No mouse/consumer reports are used.
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
- **Arrow mode**: `KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT` (0x52, 0x51, 0x50, 0x4F)
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
arduino-cli compile --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd

# Generic ESP32-S3
arduino-cli compile --fqbn esp32:esp32:esp32s3 \
  --board-options "USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd

# Serial upload (AtomS3: hold Reset button 2-3s for download mode, LED goes green)
arduino-cli upload -p /dev/ttyACM0 --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd

# Native OTA upload (arduino-cli 1.5.1+). Must use `-l network` (protocol),
# NOT `-P` (that is the programmer flag). Default OTA port is 3232; ArduinoOTA
# must be enabled in firmware (it is). Use the device IP, not the hostname.
arduino-cli compile --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd \
  && arduino-cli upload -p <ip> -l network --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  --upload-field port=3232 --upload-field password="" \
  /home/pi/touchwasd

# Fallback OTA upload via espota.py (path version 3.3.8 must match installed esp32 core)
arduino-cli compile --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd --output-dir /tmp/touchwasd-build \
  && python3 /home/pi/.arduino15/packages/esp32/hardware/esp32/3.3.8/tools/espota.py \
  -i <ip> -p 3232 -f /tmp/touchwasd-build/touchwasd.ino.bin -r -d
# If OTA password is enabled, add: -a "<password>"

## Key Design Decisions (from ikeys)
- **Reference counting**: `keyRefCount[256]` enables multi-client support. Two clients pressing `w` simultaneously increment the ref count; one releasing does not release the key.
- **Reset on disconnect**: `resetState()` clears all pressed keys when client count changes (connect/disconnect).
- **WDT**: After 5s of WebSocket inactivity, held keys/modifiers are released (only acts when keys are currently pressed).
- **USB setup**: Handled by the `ESP32USBHID` library — `HID.begin()` sets USB Class/SubClass/Protocol to 0 and calls `USB.begin()` internally before starting HID.
- **No mouse reports**: Library exposes mouse/consumer APIs, but touchWASD calls only the keyboard methods (`pressKey`/`releaseKey`/`releaseAllKeys`).

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

# Live device tests (requires AtomS3 on the network)
python3 -m pytest test/test_protocol.py --host touchwasd.local -v
```

The `--host` flag switches `MockTouchWASDDevice` for a `LiveTouchWASDDevice` connection to the real device; without it the full suite runs against the in-process mock.

Tests requiring USB HID state inspection (e.g., verifying a key is pressed) are skipped in live mode. Only protocol-level assertions run against the real device.

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
- Two-client reference counting over real WS connections
- Disconnect resets state, new client receives mode sync
- HTTP root page serving

## Calibration Notes
- The SVG uses a 200x200 viewBox. Outer circle r=96, inner cutout r=28.
- The top slice (W) is centered at 0° (straight up), spanning from 337.5° to 22.5° (45° arc). All other slices follow clockwise.
- The `describeArc()` function generates SVG path data for arc segments. It handles the wrap-around for the top slice correctly.