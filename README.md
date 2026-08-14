# touchWASD — Touchscreen WASD USB Keyboard

touchWASD turns an M5Stack AtomS3, a LilyGo T-Dongle-S3 / T-Dongle-S3-Plus (or any ESP32-S3) into a USB HID keyboard controlled by a circular touch overlay on your phone or tablet. Open a browser, touch a direction on the circle, and the corresponding WASD or arrow key is pressed on your computer — no software to install on the target machine.

```
[ Phone/Tablet ] --WiFi--> [ AtomS3 ] --USB--> [ Computer ]
  (touch circle          (keys pressed     (sees standard
   on web page)           via WebSocket)    USB keyboard)
```

Perfect for gaming, presentations, KVM control, or any situation where you want a wireless WASD/arrow input.

## Features

- **Zero software on the target PC** — shows up as a standard USB keyboard
- **Web-based 8-slice touch circle** — intuitive directional input from any phone or tablet
- **WASD mode** (default) — sends `W` `A` `S` `D` to the host PC
- **Arrow key mode** — sends ↑ ← ↓ → instead
- **Diagonal support** — NE/SE/SW/NW slices send two simultaneous keys (e.g., `W` + `D`)
- **Slide-typing** — drag your finger across slices; keys release from the old slice and press on the new one
- **4 sizes** — Small, Medium, Large, Full, persisted in browser storage
- **7 positions** — place the circle at center, top, bottom, or any corner
- **Auto-relocating gear** — the settings button moves out of the way when placed at top-right
- **Multi-client** — multiple tablets can connect simultaneously; key presses are reference-counted
- **WiFiManager** — configure WiFi via captive portal on first boot
- **Customizable mDNS hostname** — default `touchwasd.local`, configurable in the captive portal
- **OTA updates** — upload firmware wirelessly via native arduino-cli, `espota.py`, or browser (`/update`)
- **AtomS3 display** — shows IP, hostname, mode, and client count on the built-in 128×128 screen
- **T-Dongle-S3 display** — same status on the 160×80 ST7735 screen (T-Dongle-S3 / T-Dongle-S3-Plus)
- **Waveshare ESP32-S3-Touch-LCD-1.54 display** — same status on the 1.54" 240×240 ST7789 screen

## Hardware Requirements

| Component | Required | Notes |
|---|---|---|
| ESP32-S3 with native USB | Yes | M5Stack AtomS3, LilyGo T-Dongle-S3 / T-Dongle-S3-Plus recommended; any ESP32-S3 works |
| USB-C cable | Yes | Connects ESP32 to target computer |
| Phone / Tablet | Yes | Any device with a web browser |

## Quick Start

### 1. Flash the Firmware

#### Web Flasher (No Installation Required)

Open [https://controllercustom.github.io/touchwasd/](https://controllercustom.github.io/touchwasd/) in your browser to flash firmware directly via Web Serial — no Arduino IDE or CLI needed. Select your board type and firmware version, put the device in bootloader mode, and click **Flash Firmware**.

#### Arduino CLI

Pinned builds (use `--profile` instead of `--fqbn` for exact versions from `sketch.yaml`):

```bash
# AtomS3 (pinned via sketch.yaml)
arduino-cli compile --profile atoms3 .
# Hold Reset button 2-3s on AtomS3 for download mode (LED turns green)
arduino-cli upload -p /dev/ttyACM0 --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .

# Generic ESP32-S3 (pinned via sketch.yaml)
arduino-cli compile --profile esp32s3 .
# Serial upload (port is typically /dev/ttyUSB0 or /dev/ttyACMx)
arduino-cli upload -p /dev/ttyUSB0 --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" .

# LilyGo T-Dongle-S3 (pinned via sketch.yaml)
arduino-cli compile --profile tdongle_s3 .
# Serial upload (native USB CDC, typically /dev/ttyACM0; hold BOOT while plugging in)
arduino-cli upload -p /dev/ttyACM0 --profile tdongle_s3 .

# LilyGo T-Dongle-S3-Plus (same as base, but define T_DONGLE_S3_PLUS)
arduino-cli compile --profile tdongle_s3_plus . --build-property compiler.cpp.extra_flags=-DT_DONGLE_S3_PLUS
arduino-cli upload -p /dev/ttyACM0 --profile tdongle_s3_plus .

# Waveshare ESP32-S3-Touch-LCD-1.54 (240x240 ST7789 via Arduino_GFX / GFX Library for Arduino 1.6.0)
arduino-cli compile --profile waveshare . --build-property compiler.cpp.extra_flags=-DT_WAVESHARE_154
# Native USB CDC, typically /dev/ttyACM0; hold BOOT while plugging in, then power-cycle
arduino-cli upload -p /dev/ttyACM0 --profile waveshare .
```

> **T-Dongle-S3 note**: the display needs the vendored `TFT_eSPI` library shipped in
> `libraries/TFT_eSPI` (configured for the 160×80 ST7735). It is auto-detected at
> compile time via `__has_include(<TFT_eSPI.h>)`. No code changes needed. The board
> requires a **16 MB flash** FQBN and `USBMode=hwcdc,CDCOnBoot=cdc` for the serial port
> to exist; hold the **BOOT** button while plugging in USB to enter download mode.

> **Waveshare ESP32-S3-Touch-LCD-1.54 note**: the display uses **Arduino_GFX** (GFX
> Library for Arduino **1.6.0**) with the ESP32 core pinned to **3.2.0** — the same
> proven stack as the Waveshare examples. TFT_eSPI 2.5.43 crashes on ESP32-S3 on both
> core 3.x and 2.0.x, so the Waveshare path was switched to `-DT_WAVESHARE_154`
> selecting Arduino_GFX via the `WS154Display` adapter (see the `waveshare` profile in
> `sketch.yaml`). The board uses **8 MB OPI PSRAM** (`PSRAM=opi`) and native USB
> (`USBMode=hwcdc, CDCOnBoot=cdc`); hold the **BOOT** button while plugging in USB and
> power-cycle after flashing. To reset WiFi, hold the **PLUS** button (GPIO5) for 5
> seconds. Note that arduino-cli keeps only one esp32 core version installed at a
> time, so compiling the `waveshare` profile auto-installs core 3.2.0 and compiling
> the other profiles auto-installs 3.3.10 again.

> **Flash from a different computer**: the `upload/` directory carries precompiled
> binaries and `./upload.sh` / `./upload_plus.sh` scripts for both T-Dongle-S3 boards.
> Copy `upload/` to the machine with the board and run `./upload.sh [PORT]`.

#### Arduino IDE

1. Add `https://espressif.github.io/arduino-esp32/package_esp32_index.json` to *Additional Boards Manager URLs*
2. Install **ESP32** board package and libraries: **WiFiManager**, **M5GFX** (AtomS3 only), **WebSockets**, **TFT_eSPI** (T-Dongle-S3 only, see `libraries/`), and **GFX Library for Arduino** (Waveshare only). The USB HID keyboard library is built into the ESP32 core — no additional install needed.
3. Select **M5AtomS3** (or **ESP32S3 Dev Module** for generic boards)
4. Set *Tools → USB Mode → **USB-OTG (TinyUSB)***
5. Set *Tools → USB CDC On Boot → **Disabled***
6. AtomS3 only: *Tools → Partition Scheme → **8M with spiffs (3MB APP/1.5MB SPIFFS)***
7. Open `touchwasd.ino` and upload

> **AtomS3 bootloader mode**: With CDC ACM disabled, press and hold the small Reset button for 2–3 seconds. The LED turns green solid. Upload immediately after.

### 2. Connect to WiFi

On first boot, the ESP32 starts an access point named **touchWASD-Config**. Connect to it with your phone — a captive portal opens. Select your WiFi network and enter the password.

### 3. Open the Touch Overlay

Once connected, open a browser on any device on the same network:

```
http://touchwasd.local
```

A circular 8-slice touch overlay appears. Tap or drag on the circle to send keystrokes to the host computer.

### 4. Plug into the Host Computer

Connect the ESP32 to the computer via its **native USB port**. It enumerates as a standard USB HID keyboard — no drivers needed.

## Usage

### Touch Circle

The circle is divided into 8 slices (45° each), centered at 0° (straight up):

| Slice | Label | Keys Sent |
|-------|-------|-----------|
| North (top) | **W** ↑ | `W` |
| Northeast | **W+D** ↗ | `W` + `D` |
| East (right) | **D** → | `D` |
| Southeast | **D+S** ↘ | `D` + `S` |
| South (bottom) | **S** ↓ | `S` |
| Southwest | **S+A** ↙ | `S` + `A` |
| West (left) | **A** ← | `A` |
| Northwest | **A+W** ↖ | `A` + `W` |

**Single tap**: Press and release — sends the key(s) then releases immediately.

**Hold**: Sends and holds the key(s). Release your finger to release.

**Slide**: Drag across slices — held keys release and new ones press as you cross slice boundaries.

### Mode Switch

Tap the ⚙ cog button to open the settings panel. From here you can:

- **USB output**: toggle between WASD and Arrow keys (persisted on the device)
- **Size**: choose Small, Medium, Large, or Full (persisted in browser)
- **Position**: place the circle at center, top, bottom, or any corner (persisted in browser)
- **Appearance**: "Clean" shows arrow symbols only; "Labels" adds WASD text and directional hints (default: Clean)

The settings panel adapts to screen size — sections arrange side-by-side on desktops/tablets ≥769px wide, and stack vertically on mobile. Rotating your phone auto-switches between layouts. The cog button also auto-relocates to avoid overlapping the circle.

### Multiple Devices

Open `http://touchwasd.local` on multiple phones or tablets. All clients share the same key state — pressing `W` on one device and `D` on another simultaneously produces `W`+`D`. Reference counting ensures keys release only when every client has released the key.

## OTA Updates

Once the device is online and connected, upload firmware wirelessly.

**Native arduino-cli OTA** (arduino-cli 1.5.1+). Pass the device **IP** (or hostname) directly to `-p` with `--protocol network` (without it arduino-cli tries to open the address as a serial port). Default OTA port is 3232; ArduinoOTA must be enabled in firmware (it is). A disabled OTA password is passed as `--upload-field password=""`:

```bash
arduino-cli compile --profile atoms3 . \
  && arduino-cli upload -p <ip> --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  --upload-field port=3232 --upload-field password="" \
  --protocol network \
  .
```

**espota.py fallback** (path must match installed esp32 core):

```bash
arduino-cli compile --profile atoms3 . --output-dir /tmp/touchwasd-build \
  && python3 ~/.arduino15/packages/esp32/hardware/esp32/3.3.10/tools/espota.py \
  -i touchwasd.local -f /tmp/touchwasd-build/touchwasd.ino.bin -r -d
# If OTA password is enabled, add: -a "<password>"
```

Or use the web interface at `http://touchwasd.local/update`.

OTA works identically for the T-Dongle-S3 / T-Dongle-S3-Plus / Waveshare ESP32-S3-Touch-LCD-1.54 boards — compile with their profile (add `--build-property compiler.cpp.extra_flags=-DT_WAVESHARE_154` for the Waveshare) and pass the device IP to `--protocol network`:

```bash
arduino-cli compile --profile tdongle_s3 . \
  && arduino-cli upload -p <ip> --fqbn "esp32:esp32:esp32s3:FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=disabled,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio,LoopCore=1" \
  --upload-field port=3232 --upload-field password="" \
  --protocol network \
  .
```

### OTA Password

By default, OTA updates require no password — anyone on your network can upload firmware. To enable password protection:

1. Open `touchwasd.ino` and uncomment this line near the top:
   ```cpp
   // #define OTA_PASS "your-password-here"
   ```
2. Change `"your-password-here"` to your chosen password.
3. Recompile and upload via serial.

Password applies to ArduinoOTA — native arduino-cli OTA (`--upload-field password="<password>"`), `espota.py -a "<password>"`, and the Web OTA interface (HTTP Basic Auth).

## Resetting WiFi

Hold the built-in button for 5 seconds:

- **AtomS3**: hold GPIO41 button (display shows "Resetting WiFi...")
- **Generic**: hold BOOT button (GPIO0)
- **T-Dongle-S3 / T-Dongle-S3-Plus**: hold BOOT button (GPIO0)
- **Waveshare ESP32-S3-Touch-LCD-1.54**: hold the PLUS button (GPIO5)

WiFi credentials are erased and the device reboots into the `touchWASD-Config` captive portal.

## Build Reference

### Board Options

```
AtomS3:   esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default
Generic:  esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default
T-Dongle-S3 / Plus: esp32:esp32:esp32s3:FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=disabled,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio,LoopCore=1
Waveshare ESP32-S3-Touch-LCD-1.54: esp32:esp32:esp32s3:FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi,USBMode=hwcdc,CDCOnBoot=cdc
```

### Required Libraries

- **WiFiManager** by tzapu
- **WebSockets** by Markus Sattler
- **M5GFX** by M5Stack (AtomS3 only — optional for generic boards)
- **TFT_eSPI** by Bodmer — vendored in `libraries/TFT_eSPI` (T-Dongle-S3 / Plus, configured for the 160×80 ST7735)
- **GFX Library for Arduino** by Moon On Our Nation — Waveshare ESP32-S3-Touch-LCD-1.54 only (240×240 ST7789 via Arduino_GFX)
- USB HID keyboard is built into the ESP32 core (`USB.h`) — no additional library needed

### Versions

Pinned in `sketch.yaml` for reproducible builds:

| Component | Version | Notes |
|---|---|---|
| ESP32 Core | 3.3.10 | Pinned in `sketch.yaml` (waveshare profile pins 3.2.0) |
| WiFiManager | 2.0.17 | Pinned in `sketch.yaml` |
| WebSockets | 2.7.2 | Pinned in `sketch.yaml` |
| M5GFX | 0.2.26 | Pinned in `sketch.yaml` (AtomS3 only) |
| TFT_eSPI | 2.5.43 | Vendored in `libraries/TFT_eSPI` (T-Dongle-S3 only) |
| GFX Library for Arduino | 1.6.0 | Pinned in `sketch.yaml` (Waveshare only; requires core 3.2.0) |


## Changelog

### v1.2.0 (2026-08-14)
- **Waveshare ESP32-S3-Touch-LCD-1.54 support**: 240×240 ST7789 status display via **Arduino_GFX** (GFX Library for Arduino 1.6.0) on core **3.2.0** — the proven Waveshare example stack. TFT_eSPI 2.5.43 crashes on ESP32-S3 on both core 3.x and 2.0.x (StoreProhibited in `begin_tft_write`), so the earlier vendored-TFT_eSPI approach was replaced; a `WS154Display` adapter in `touchwasd.ino` exposes the sketch's TFT_eSPI API subset over Arduino_GFX. `waveshare` profile in `sketch.yaml` (16 MB flash, OPI PSRAM, hwcdc, core 3.2.0). WiFi reset via the PLUS button (GPIO5).

### v1.0.5 (2026-07-28)
- **iOS Safari diagonal arrow fix**: appended Unicode variation selector `\uFE0E` to diagonal glyphs (`↗`, `↘`, etc.) so they render as plain text instead of emoji-style buttons on iOS Safari
- **Diagonal font sizing**: reduced diagonal label sizes (18px primary, 11px secondary) for visual parity with cardinal slices at equal font weight — diagonals are inherently wider glyphs and would otherwise dominate the slice area
- **Appearance toggle** ("Clean" arrows-only / "Labels" WASD text + directional hints), persisted in `localStorage` as `tw-lk`
- Responsive settings panel: side-by-side layout on screens ≥769px, vertical stack below

### v1.0.4 (2026-07-28)
- Initial release with WiFiManager captive portal, OTA updates, and multi-client reference counting

## Tests

Python 3 test suite at `test/`. Tests both core logic and wire protocol:

```bash
# Mock device tests (no hardware needed)
python3 -m pytest test/ -v

# Live device tests (requires AtomS3 on the network)
python3 -m pytest test/test_protocol.py --host touchwasd.local -v
```

With `python3-evdev` installed and the device's USB HID keyboard visible to the host (e.g. `/dev/input/event5`), the live tests also assert the **actual USB HID keystrokes** the device emits — see `test/test_hid.py`. Without evdev (or no `--host`), those HID-inspection assertions are skipped and only protocol-level checks run.

### `test/test_core.py` — Unit tests (stdlib only, no dependencies)
- `charToHID()` lookup table validation against every ASCII character
- Key state management: press/release lifecycle, 6-key limit, swap-removal
- Reference counting: multi-client, overflow cap at 255
- Mode mapping: WASD vs Arrow key translation
- HID report format: 8-byte report structure

### `test/test_protocol.py` — Integration tests (requires `websocket-client`)
- `MockTouchWASDDevice`: simulated ESP32 with WS+HTTP servers; `--host` flag connects to a real device instead
- WebSocket handshake, key press/release, diagonal, release-all (`~`)
- Mode switch round-trip (`#MODE:wasd` / `#MODE:arrows`)
- Two-client reference counting over real WS connections
- Disconnect resets state, new client receives mode sync
- HTTP root page serving

### `test/test_hid.py` — Live USB HID inspection (requires `--host` + `python3-evdev`)
- Reads the device's real keystrokes via evdev (`/dev/input/event*`)
- Press/release round-trip, diagonal two-key, arrow-mode mapping, release-all
- Verifies the monitor reports HID usage codes (not raw evdev codes)

### `test/test_e2e.py` — Latency measurement (standalone, no pytest)
- Sends key presses over WebSocket, observes HID arrival via evdev `select.select()`
- Measures end-to-end latency (WS send → USB HID on host) with statistical report
- Optional `--serial` flag reads `[TIMING]` markers for firmware processing time split (requires firmware compiled with `-DTIMING_OUTPUT`)
- Configurable pass/fail threshold (default 20ms p99)
- Usage: `python3 test/test_e2e.py --host <ip> [--serial /dev/ttyUSB0] [--samples 50]`

### Live Test Prerequisites

To run live tests with USB HID inspection against a plugged-in device:

1. Install `python3-evdev`: `pip install python3-evdev`
2. Ensure your user can read `/dev/input/event*`. On Ubuntu 24.04 and similar distros, add yourself to the **input** group:
   ```bash
   sudo usermod -aG input $USER
   # Log out and back in (or run `newgrp input`) for the change to take effect
   ```
3. Run with both flags so tests connect over WiFi *and* inspect USB HID locally:
   ```bash
   python3 -m pytest test/ --host 192.168.1.xxx -v
   ```

The `--hid-name` flag can override the auto-detected keyboard name substring if needed (e.g., `--hid-name "ESP32S3_DEV"`).

## License

MIT