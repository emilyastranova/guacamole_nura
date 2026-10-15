#!/usr/bin/env bash
# fastboot boot with the recovery steps the OnePlus 7 Pro ABL needs.
#
# The bootloader often stalls at "Sending 'boot.img'" or answers "Load Error".
# When it stalls, fastboot never returns and the device still enumerates
# (18d1:d00d), so a plain retry hangs as well. Resetting the USB device from
# the host and asking the ABL to restart itself clears the state reliably.
#
#   scripts/fastboot_boot.sh [boot.img]
set -u

IMG=${1:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/build/boot.img"}
[ -f "$IMG" ] || { echo "no such image: $IMG" >&2; exit 1; }

usb_reset() {
	python3 - <<'EOF'
import fcntl, glob
for dev in glob.glob('/dev/bus/usb/*/*'):
    try:
        with open(dev, 'rb+') as f:
            d = f.read(18)
            if (d[8] | d[9] << 8, d[10] | d[11] << 8) == (0x18d1, 0xd00d):
                fcntl.ioctl(f, 0x5514)  # USBDEVFS_RESET
                print("reset", dev)
    except OSError:
        pass
EOF
}

wait_fastboot() {
	for _ in $(seq 1 "${1:-30}"); do
		fastboot devices 2>/dev/null | grep -q fastboot && return 0
		sleep 2
	done
	return 1
}

try_boot() {
	timeout 15 fastboot boot "$IMG" 2>&1 | tail -2 | tee /dev/stderr | grep -q 'Booting.*OKAY'
}

wait_fastboot 40 || { echo "no fastboot device" >&2; exit 1; }
for attempt in 1 2 3; do
	try_boot && exit 0
	echo "attempt $attempt stalled; resetting the USB device and restarting the bootloader" >&2
	usb_reset
	sleep 2
	timeout 20 fastboot reboot bootloader >/dev/null 2>&1
	wait_fastboot 30 || break
done
echo "fastboot boot failed; restart the bootloader on the phone by hand" >&2
exit 1
