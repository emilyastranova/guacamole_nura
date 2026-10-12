#!/usr/bin/env bash
set -e

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROOT_ROOTFS="/home/emily/.local/var/pmbootstrap/chroot_rootfs_oneplus-guacamole"
OUTPUT_DIR="${WORKSPACE_DIR}/build"
BOOTIMG="${OUTPUT_DIR}/boot.img"

echo "=== Building OnePlus 7 Pro (guacamole) Mainline boot.img ==="

mkdir -p "${OUTPUT_DIR}"

# 1. Prepare uncompressed kernel
echo "[1/4] Decompressing kernel Image..."
# KERNEL_DIR selects an extracted kernel package (default: build/kernel_r6).
# Its modules must match the ones installed on the phone's rootfs.
KERNEL_DIR="${KERNEL_DIR:-${WORKSPACE_DIR}/build/kernel_r6}"
if [ -f "${KERNEL_DIR}/boot/vmlinuz" ]; then
    echo "Using kernel from ${KERNEL_DIR}"
    zcat "${KERNEL_DIR}/boot/vmlinuz" > /tmp/Image
elif [ -f "${CHROOT_ROOTFS}/boot/vmlinuz" ]; then
    zcat "${CHROOT_ROOTFS}/boot/vmlinuz" > /tmp/Image
elif [ -f "${CHROOT_ROOTFS}/boot/Image" ]; then
    cp "${CHROOT_ROOTFS}/boot/Image" /tmp/Image
else
    echo "ERROR: Kernel not found!"
    exit 1
fi

# 2. Patch and compile DTB with Qualcomm board IDs and ramoops
echo "[2/4] Compiling DTB with Qualcomm ABL IDs..."
python3 "${WORKSPACE_DIR}/scripts/patch_dtb.py"

# 3. Locate initramfs
echo "[3/4] Locating initramfs..."
if [ -n "${INITRAMFS:-}" ]; then
    echo "Using initramfs override ${INITRAMFS}"
elif [ -f "/tmp/device_initramfs_r4" ]; then
    INITRAMFS="/tmp/device_initramfs_r4"
else
    INITRAMFS="${CHROOT_ROOTFS}/boot/initramfs"
fi
if [ ! -f "${INITRAMFS}" ]; then
    echo "ERROR: initramfs not found at ${INITRAMFS}!"
    exit 1
fi

# 4. Generate boot.img with mkbootimg (Header Version 2)
echo "[4/4] Packing boot.img (Header Version 2)..."
mkbootimg \
    --header_version 2 \
    --kernel /tmp/Image \
    --ramdisk "${INITRAMFS}" \
    --dtb /tmp/custom_guacamole.dtb \
    --base 0x00000000 \
    --kernel_offset 0x00008000 \
    --ramdisk_offset 0x01000000 \
    --second_offset 0x00000000 \
    --tags_offset 0x00000100 \
    --dtb_offset 0x01f00000 \
    --pagesize 4096 \
    --os_version 10.0.0 \
    --os_patch_level 2021-01 \
    --cmdline "console=tty0 console=ttyMSM0,115200n8 earlycon ramoops.mem_address=0xa9800000 ramoops.mem_size=0x400000 ramoops.record_size=0x40000 ramoops.console_size=0x40000 ramoops.pmsg_size=0x200000 pmOS_loglevel=8 PMOS_NO_OUTPUT_REDIRECT" \
    -o "${BOOTIMG}"

# 5. Append AVB footer for Qualcomm ABL / libavb authentication
echo "[5/5] Appending AVB hash footer..."
avbtool add_hash_footer \
    --image "${BOOTIMG}" \
    --dynamic_partition_size \
    --partition_name boot \
    --algorithm NONE

echo "SUCCESS! Generated: ${BOOTIMG} ($(ls -lh "${BOOTIMG}" | awk '{print $5}'))"
