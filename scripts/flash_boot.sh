#!/usr/bin/env bash
set -e

# Flashes or test-boots the generated boot.img to the connected OnePlus 7 Pro.
# Usage:
#   ./scripts/flash_boot.sh test    # Safe: fastboot boot (does not touch flash)
#   ./scripts/flash_boot.sh flash   # Permanent: fastboot flash boot

ACTION="${1:-test}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== OnePlus 7 Pro Fastboot Helper ==="

if ! command -v fastboot &> /dev/null; then
    echo "Notice: host 'fastboot' not found in PATH."
    echo "Using 'pmbootstrap flasher' (runs fastboot inside native chroot)..."
    if [ "$ACTION" == "test" ]; then
        echo "Executing: pmbootstrap flasher boot"
        exec pmbootstrap flasher boot
    elif [ "$ACTION" == "flash" ]; then
        echo "Executing: pmbootstrap flasher flash_kernel"
        exec pmbootstrap flasher flash_kernel
    else
        echo "Invalid option: $ACTION. Use 'test' or 'flash'."
        exit 1
    fi
fi

echo "Checking fastboot devices..."
DEVICE=$(fastboot devices | awk '{print $1}' | head -n 1)
if [ -z "$DEVICE" ]; then
    echo "Error: No fastboot devices found. Please boot phone into bootloader mode."
    exit 1
fi
echo "Connected device: $DEVICE"

# Determine boot.img path
BOOTIMG=""
if [ -f "$REPO_ROOT/build/boot.img" ]; then
    BOOTIMG="$REPO_ROOT/build/boot.img"
elif [ -f "$REPO_ROOT/boot.img" ]; then
    BOOTIMG="$REPO_ROOT/boot.img"
else
    # Check default pmbootstrap chroot output
    CHROOT_BOOTIMG="$(pmbootstrap -q config work)/chroot_rootfs_oneplus-guacamole/boot/boot.img" 2>/dev/null || true
    if [ -f "$CHROOT_BOOTIMG" ]; then
        BOOTIMG="$CHROOT_BOOTIMG"
    fi
fi

if [ -z "$BOOTIMG" ] || [ ! -f "$BOOTIMG" ]; then
    echo "Notice: No boot.img found in repo root or pmbootstrap chroot."
    echo "You can generate one using: pmbootstrap flasher boot"
    echo "Or place your boot.img in the repository root."
    exit 1
fi

echo "Using boot image: $BOOTIMG"

if [ "$ACTION" == "test" ]; then
    echo "Testing boot image via 'fastboot boot $BOOTIMG' (Non-destructive)..."
    fastboot boot "$BOOTIMG"
elif [ "$ACTION" == "flash" ]; then
    echo "Flashing boot partition via 'fastboot flash boot $BOOTIMG'..."
    fastboot flash boot "$BOOTIMG"
else
    echo "Invalid option: $ACTION. Use 'test' or 'flash'."
    exit 1
fi
