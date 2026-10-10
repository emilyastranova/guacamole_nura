#!/usr/bin/env bash
set -e

# Pulls ramoops / pstore crash logs from the OnePlus 7 Pro via ADB
# (Run this after rebooting into TWRP or a working recovery following a kernel panic)

LOG_DIR="$(pwd)/logs/ramoops_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "=== Pulling Ramoops / pstore Logs ==="

if ! command -v adb &> /dev/null; then
    echo "Error: adb command not found."
    exit 1
fi

echo "Connecting to device..."
adb wait-for-device

echo "Mounting pstore if needed..."
adb shell "mount -t pstore pstore /sys/fs/pstore 2>/dev/null || true"

echo "Checking /sys/fs/pstore contents..."
FILES=$(adb shell "ls -1 /sys/fs/pstore 2>/dev/null" || true)

if [ -z "$FILES" ]; then
    echo "No files found in /sys/fs/pstore on device."
    echo "Checking dmesg buffer fallback..."
    adb shell "dmesg" > "$LOG_DIR/dmesg.log" 2>/dev/null || true
    echo "Saved current dmesg to $LOG_DIR/dmesg.log"
else
    echo "Found pstore files:"
    echo "$FILES"
    adb pull /sys/fs/pstore/ "$LOG_DIR/"
    echo "Successfully copied pstore logs to: $LOG_DIR"
fi
