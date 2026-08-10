#!/usr/bin/env bash
# Upload the precompiled touchWASD firmware (Plus build) to a LilyGo T-Dongle-S3-Plus.
#
# Usage:
#   ./upload_plus.sh [PORT]
#
#   PORT  serial port to use (default: /dev/ttyACM0)
#
# Requirements on the machine running this script:
#   - arduino-cli  (https://arduino.github.io/arduino-cli/)
#   - Network access on first run, if the ESP32 core is not installed yet.
#
# The binaries in ./build/tdongle_s3_plus were built with:
#   arduino-cli compile --profile tdongle_s3_plus . --output-dir upload/build/tdongle_s3_plus \
#     --build-property compiler.cpp.extra_flags=-DT_DONGLE_S3_PLUS
set -euo pipefail

PORT="${1:-/dev/ttyACM0}"
FQBN="esp32:esp32:esp32s3:FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=disabled,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio,LoopCore=1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="${SCRIPT_DIR}/build/tdongle_s3_plus"

if ! command -v arduino-cli >/dev/null 2>&1; then
  echo "ERROR: arduino-cli not found." >&2
  echo "Install it from https://arduino.github.io/arduino-cli/ and re-run." >&2
  exit 1
fi

if ! arduino-cli core list 2>/dev/null | grep -q "esp32:esp32"; then
  echo "esp32:esp32 core not installed. Installing..."
  arduino-cli config add board_manager.additional_urls \
    https://espressif.github.io/arduino-esp32/package_esp32_index.json
  arduino-cli core update-index
  arduino-cli core install esp32:esp32
fi

echo "Uploading T-Dongle-S3-Plus touchWASD firmware to ${PORT} ..."
echo "If the upload fails, hold the BOOT button while plugging in USB to enter download mode."
arduino-cli upload -p "${PORT}" --fqbn "${FQBN}" --input-dir "${INPUT_DIR}" -t
echo "Upload finished."
