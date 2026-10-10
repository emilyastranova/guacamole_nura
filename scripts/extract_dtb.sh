#!/usr/bin/env bash
set -e

# Extracts the live device tree blob from a booted Android / TWRP session via ADB
# and decompiles it to human-readable device tree source (device.dts).

OUTPUT_DIR="$(pwd)/extracted_dtb"
mkdir -p "$OUTPUT_DIR"

echo "=== Extracting Device Tree Blob via ADB ==="

if ! command -v adb &> /dev/null; then
    echo "Error: adb command not found. Please install android-tools / adb."
    exit 1
fi

echo "[1/4] Checking ADB connection..."
STATE=$(adb get-state 2>/dev/null || true)
if [ "$STATE" != "device" ] && [ "$STATE" != "recovery" ]; then
    echo "Waiting for device or recovery..."
    adb wait-for-any-recovery 2>/dev/null || adb wait-for-any-device 2>/dev/null || true
fi
adb root 2>/dev/null || echo "Note: If adb root fails, ensure adbd has root permissions or TWRP is booted."

echo "[2/4] Dumping /sys/firmware/fdt to /sdcard/device.dtb..."
adb shell "su -c 'dd if=/sys/firmware/fdt of=/sdcard/device.dtb status=none' 2>/dev/null || dd if=/sys/firmware/fdt of=/sdcard/device.dtb status=none"

echo "[3/4] Pulling device.dtb to $OUTPUT_DIR..."
adb pull /sdcard/device.dtb "$OUTPUT_DIR/device.dtb"
adb shell "rm -f /sdcard/device.dtb"

echo "[4/4] Decompiling DTB to DTS..."
if command -v dtc &> /dev/null; then
    dtc -I dtb -O dts -o "$OUTPUT_DIR/device.dts" "$OUTPUT_DIR/device.dtb"
    echo "Saved decompiled device tree to: $OUTPUT_DIR/device.dts"

    echo ""
    echo "=== Key Hardware Signatures in Extracted DTS ==="
    echo "--- Board IDs & Models ---"
    grep -E "model|compatible|qcom,msm-id|qcom,board-id" "$OUTPUT_DIR/device.dts" | head -n 15 || true

    echo "--- Framebuffer / Splash Memory ---"
    grep -n -C 5 "cont_splash_region" "$OUTPUT_DIR/device.dts" || true
else
    echo "Warning: dtc (device-tree-compiler) is not installed."
    echo "Install dtc (e.g., 'sudo dnf install dtc' or 'sudo apt install device-tree-compiler') and run:"
    echo "  dtc -I dtb -O dts -o $OUTPUT_DIR/device.dts $OUTPUT_DIR/device.dtb"
fi

echo "Done!"
