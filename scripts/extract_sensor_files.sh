#!/usr/bin/env bash
# Collect the files the SLPI sensor DSP needs from a OnePlus 7 Pro running
# this port, over SSH, into a tarball that device-oneplus-guacamole installs.
#
#   scripts/extract_sensor_files.sh [user@host] [outdir]
#
# Reads three stock partitions read-only (vendor_b, dsp_b, persist) and packs:
#   sensors/config/*.json, sensors/sns_reg.conf   from vendor_b /etc/sensors
#   sdsp/*                                        from dsp_b   /sdsp
#   registry-default/registry/*                   from persist /sensors/registry
# The registry is this phone's factory calibration; the package installs it
# only as the fallback for a phone whose persist partition cannot be read.
set -euo pipefail

host=${1:-user@172.16.42.1}
outdir=${2:-device/testing/device-oneplus-guacamole}
stamp=$(date +%Y%m%d)
base="guacamole-sensors-$stamp"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

ssh "$host" 'set -e; P=147147; s(){ echo "$P" | sudo -S -p "" "$@"; }
	t=$(mktemp -d); s mkdir -p /mnt/gsx
	s mount -o ro /dev/disk/by-partlabel/vendor_b /mnt/gsx
	s sh -c "mkdir -p $t/sensors && cp -r /mnt/gsx/etc/sensors/config $t/sensors/ && cp /mnt/gsx/etc/sensors/sns_reg_config $t/sensors/sns_reg.conf"
	s umount /mnt/gsx
	s mount -o ro /dev/disk/by-partlabel/dsp_b /mnt/gsx
	s sh -c "mkdir -p $t/sdsp && cp /mnt/gsx/sdsp/* $t/sdsp/"
	s umount /mnt/gsx
	s mount -o ro,noload /dev/disk/by-partlabel/persist /mnt/gsx
	s sh -c "mkdir -p $t/registry-default && cp -r /mnt/gsx/sensors/registry/registry $t/registry-default/"
	s umount /mnt/gsx; s rmdir /mnt/gsx
	s sh -c "chown -R $(id -u) $t && cd $t && tar cf - ." ; s rm -rf "$t"' > "$tmp/raw.tar"

mkdir -p "$tmp/$base"
tar -xf "$tmp/raw.tar" -C "$tmp/$base"
n=$(find "$tmp/$base" -type f | wc -l)
mkdir -p "$outdir"
# Deterministic: sorted entries, fixed mtime and owner.
tar --sort=name --mtime='1970-01-01 00:00Z' --owner=0 --group=0 --numeric-owner \
	-C "$tmp" -cf - "$base" | gzip -n > "$outdir/$base.tar.gz"
echo "$outdir/$base.tar.gz ($n files)"
