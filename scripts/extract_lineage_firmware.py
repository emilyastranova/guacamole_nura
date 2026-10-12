#!/usr/bin/env python3
"""Extract the OnePlus 7 Pro modem and WCN3990 Wi-Fi firmware from a LineageOS OTA.

The OxygenOS 10/11 WLAN firmware (WLAN.HL.3.2.0) rejects station vdev start
under mainline ath10k. The OxygenOS 12-era set shipped in LineageOS OTAs
(WLAN.HL.3.0.c8) connects on 2.4 and 5 GHz. This script rebuilds the `modem`
partition from the OTA's payload.bin and packs the files the
firmware-oneplus-guacamole package installs:

    qcom/sm8150/oneplus7/modem.mdt, modem.bNN, modemr.jsn, modemuw.jsn,
    wlanmdsp.mbn
    ath10k/WCN3990/hw1.0/board-2.bin   (bdwlan.bin as 'bus=snoc,qmi-board-id=ff')
    qca/crbtfw21.tlv, qca/crnv21.bin   (WCN3990 Bluetooth, from the bluetooth partition)

Usage:
    scripts/extract_lineage_firmware.py <lineage-*-guacamole-signed.zip> [outdir]

Writes <outdir>/firmware-oneplus-guacamole-<lineage build>.tar.gz (deterministic:
sorted entries, fixed mtime/owner) plus a VERSIONS file. Requires `mcopy`
(mtools) to read the FAT modem image.
"""
import bz2
import gzip
import io
import lzma
import os
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile

MODEM_DIR = "qcom/sm8150/oneplus7"
BT_DIR = "qca"
BT_FILES = ("crbtfw21.tlv", "crnv21.bin")
BOARD_PATH = "ath10k/WCN3990/hw1.0/board-2.bin"
BOARD_NAME = b"bus=snoc,qmi-board-id=ff"


def varint(b, i):
    v = s = 0
    while True:
        c = b[i]
        v |= (c & 0x7F) << s
        i += 1
        s += 7
        if c < 0x80:
            return v, i


def fields(b):
    i = 0
    while i < len(b):
        key, i = varint(b, i)
        fn, wt = key >> 3, key & 7
        if wt == 0:
            v, i = varint(b, i)
        elif wt == 1:
            v = b[i:i + 8]
            i += 8
        elif wt == 5:
            v = b[i:i + 4]
            i += 4
        elif wt == 2:
            ln, i = varint(b, i)
            v = b[i:i + ln]
            i += ln
        else:
            raise ValueError("unsupported protobuf wire type %d" % wt)
        yield fn, v


def extract_partition(ota_zip, name, out_path):
    """Rebuild one partition from a full-OTA payload.bin."""
    z = zipfile.ZipFile(ota_zip)
    if z.getinfo("payload.bin").compress_type != zipfile.ZIP_STORED:
        raise SystemExit("payload.bin is compressed inside the zip; unsupported")
    f = z.open("payload.bin")
    hdr = f.read(24)
    if hdr[:4] != b"CrAU":
        raise SystemExit("not an A/B OTA payload")
    mlen = struct.unpack(">Q", hdr[12:20])[0]
    siglen = struct.unpack(">I", hdr[20:24])[0]
    manifest = f.read(mlen)
    data_base = 24 + mlen + siglen
    block_size = 4096
    parts = []
    for fn, v in fields(manifest):
        if fn == 3:
            block_size = v
        elif fn == 13:
            parts.append(v)
    for p in parts:
        pname, ops = None, []
        for fn, v in fields(p):
            if fn == 1:
                pname = v.decode()
            elif fn == 8:
                ops.append(v)
        if pname != name:
            continue
        with open(out_path, "wb") as out:
            for op in ops:
                typ = off = ln = 0
                exts = []
                for fn, v in fields(op):
                    if fn == 1:
                        typ = v
                    elif fn == 2:
                        off = v
                    elif fn == 3:
                        ln = v
                    elif fn == 6:
                        d = dict(fields(v))
                        exts.append((d.get(1, 0), d.get(2, 0)))
                if typ == 6:  # ZERO
                    for sb, nb in exts:
                        out.seek(sb * block_size)
                        out.write(b"\0" * nb * block_size)
                    continue
                f.seek(data_base + off)
                blob = f.read(ln)
                if typ == 0:
                    data = blob
                elif typ == 1:
                    data = bz2.decompress(blob)
                elif typ == 8:
                    data = lzma.decompress(blob)
                else:
                    raise SystemExit("unsupported operation type %d (incremental OTA?)" % typ)
                pos = 0
                for sb, nb in exts:
                    out.seek(sb * block_size)
                    out.write(data[pos:pos + nb * block_size])
                    pos += nb * block_size
        return
    raise SystemExit("partition %r not found in payload" % name)


def board2(bdwlan):
    def ie(ie_id, body):
        return struct.pack("<II", ie_id, len(body)) + body + b"\0" * ((4 - len(body) % 4) % 4)

    magic = b"QCA-ATH10K-BOARD\0"
    magic += b"\0" * ((4 - len(magic) % 4) % 4)
    return magic + ie(0, ie(0, BOARD_NAME) + ie(1, bdwlan))


def version_string(path, prefix):
    m = re.search(rb"QC_IMAGE_VERSION_STRING=(" + re.escape(prefix) + rb"[\x21-\x7e]*)",
                  open(path, "rb").read())
    return m.group(1).decode() if m else "unknown"


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    ota = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) == 3 else "build"
    if not shutil.which("mcopy"):
        raise SystemExit("mcopy (mtools) is required")
    m = re.search(r"lineage-([0-9.]+-[0-9]{8})", os.path.basename(ota))
    build = m.group(1) if m else "unknown"

    with tempfile.TemporaryDirectory() as tmp:
        img = os.path.join(tmp, "modem.img")
        extract_partition(ota, "modem", img)
        subprocess.run(["mcopy", "-s", "-n", "-i", img, "::/image", tmp], check=True)
        src = os.path.join(tmp, "image")

        files = {}
        for name in sorted(os.listdir(src)):
            if re.fullmatch(r"modem\.(mdt|b[0-9]{2})|modemr\.jsn|modemuw\.jsn|wlanmdsp\.mbn", name):
                files["%s/%s" % (MODEM_DIR, name)] = open(os.path.join(src, name), "rb").read()
        if "%s/modem.mdt" % MODEM_DIR not in files or "%s/wlanmdsp.mbn" % MODEM_DIR not in files:
            raise SystemExit("modem.mdt or wlanmdsp.mbn missing from the modem partition")
        files[BOARD_PATH] = board2(open(os.path.join(src, "bdwlan.bin"), "rb").read())

        wlan = version_string(os.path.join(src, "wlanmdsp.mbn"), b"WLAN")
        modem = version_string(os.path.join(src, "modem.mdt"), b"MPSS")

        bt_img = os.path.join(tmp, "bluetooth.img")
        extract_partition(ota, "bluetooth", bt_img)
        bt_dir = os.path.join(tmp, "bt")
        os.makedirs(bt_dir)
        subprocess.run(["mcopy", "-s", "-n", "-i", bt_img, "::/image", bt_dir], check=True)
        for name in BT_FILES:
            files["%s/%s" % (BT_DIR, name)] = open(os.path.join(bt_dir, "image", name), "rb").read()
        bt = version_string(os.path.join(bt_dir, "image", "crbtfw21.tlv"), b"BTFM")

    os.makedirs(outdir, exist_ok=True)
    base = "firmware-oneplus-guacamole-%s" % build
    tar_path = os.path.join(outdir, base + ".tar.gz")
    with open(tar_path, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for path in sorted(files):
                    data = files[path]
                    ti = tarfile.TarInfo("%s/%s" % (base, path))
                    ti.size, ti.mtime, ti.mode = len(data), 0, 0o644
                    ti.uid = ti.gid = 0
                    ti.uname = ti.gname = "root"
                    tar.addfile(ti, io.BytesIO(data))
    with open(os.path.join(outdir, base + ".VERSIONS"), "w") as v:
        v.write("source=%s\nwlan=%s\nmodem=%s\nbluetooth=%s\nfiles=%d\n"
                % (os.path.basename(ota), wlan, modem, bt, len(files)))
    print(tar_path)
    print("wlan  %s\nmodem %s\nbt    %s\nfiles %d" % (wlan, modem, bt, len(files)))


if __name__ == "__main__":
    main()
