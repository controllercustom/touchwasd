# touchWASD — Touchscreen WASD USB Keyboard

touchWASD turns an M5Stack AtomS3 (or any ESP32-S3) into a USB HID keyboard controlled by a circular touch overlay on your phone or tablet. Open a browser, touch a direction on the circle, and the corresponding WASD or arrow key is pressed on your computer — no software to install on the target machine.

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

## Hardware Requirements

| Component | Required | Notes |
|---|---|---|
| ESP32-S3 with native USB | Yes | M5Stack AtomS3 recommended; any ESP32-S3 works |
| USB-C cable | Yes | Connects ESP32 to target computer |
| Phone / Tablet | Yes | Any device with a web browser |

## Quick Start

### 1. Flash the Firmware

#### Arduino CLI

```bash
# AtomS3
arduino-cli compile --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd

# Hold Reset button 2-3s on AtomS3 for download mode (LED turns green)
arduino-cli upload -p /dev/ttyACM0 --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd
```

#### Arduino IDE

1. Add `https://espressif.github.io/arduino-esp32/package_esp32_index.json` to *Additional Boards Manager URLs*
2. Install **ESP32** board package and libraries: **WiFiManager**, **M5GFX** (AtomS3 only), **WebSockets**. Then install **ESP32USBHID** globally from its repo ZIP — see *Installing the ESP32USBHID library* below.
3. Select **M5AtomS3** (or **ESP32S3 Dev Module** for generic boards)
4. Set *Tools → USB Mode → **USB-OTG (TinyUSB)***
5. Set *Tools → USB CDC On Boot → **Disabled***
6. AtomS3 only: *Tools → Partition Scheme → **8M with spiffs (3MB APP/1.5MB SPIFFS)***
7. Open `touchwasd.ino` and upload

> **AtomS3 bootloader mode**: With CDC ACM disabled, press and hold the small Reset button for 2–3 seconds. The LED turns green solid. Upload immediately after.

### Installing the ESP32USBHID library

`ESP32USBHID` is **not** on the Arduino Library Manager — install it globally from its GitHub repo:

1. Download the ZIP: open `https://github.com/controllercustom/ESP32USBHID` and click **Code → Download ZIP** (or grab a release ZIP).
2. In the Arduino IDE, choose **Sketch → Include Library → Add .ZIP Library…** and select the downloaded `.zip`.

The IDE extracts it into your global sketchbook `libraries/` folder (e.g. `~/Arduino/libraries/ESP32USBHID`), making it available to every sketch — no manual folder copying. arduino-cli also auto-discovers it there.

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

- **Mode**: toggle between WASD and Arrow keys (persisted on the device)
- **Size**: choose Small, Medium, Large, or Full (persisted in browser)
- **Position**: place the circle at center, top, bottom, or any corner (persisted in browser)

The cog button auto-relocates to avoid overlapping the circle.

### Multiple Devices

Open `http://touchwasd.local` on multiple phones or tablets. All clients share the same key state — pressing `W` on one device and `D` on another simultaneously produces `W`+`D`. Reference counting ensures keys release only when every client has released the key.

## OTA Updates

Once the device is online and connected, upload firmware wirelessly.

**Native arduino-cli OTA** (arduino-cli 1.5.1+). Use the device **IP** and `-l network` (the network protocol flag — *not* `-P`, which is the programmer flag); default OTA port is 3232:

```bash
arduino-cli compile --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd \
  && arduino-cli upload -p <ip> -l network --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  --upload-field port=3232 --upload-field password="" \
  /home/pi/touchwasd
```

**espota.py fallback** (path version `3.3.8` must match the installed esp32 core):

```bash
arduino-cli compile --fqbn esp32:esp32:m5stack_atoms3 \
  --board-options "PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" \
  /home/pi/touchwasd --output-dir /tmp/touchwasd-build \
  && python3 /home/pi/.arduino15/packages/esp32/hardware/esp32/3.3.8/tools/espota.py \
  -i touchwasd.local -f /tmp/touchwasd-build/touchwasd.ino.bin -r -d
# If OTA password is enabled, add: -a "<password>"
```

Or use the web interface at `http://touchwasd.local/update`.

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

WiFi credentials are erased and the device reboots into the `touchWASD-Config` captive portal.

## Build Reference

### Board Options

```
AtomS3:   esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default
Generic:  esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default
```

### Required Libraries

- **WiFiManager** by tzapu
- **WebSockets** by Markus Sattler
- **ESP32USBHID** by controllercustom (install globally from the repo ZIP — see *Installing the ESP32USBHID library*)
- **M5GFX** by M5Stack (AtomS3 only)

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

## License

MIT