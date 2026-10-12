# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A bringup workspace for running postmarketOS / Nura on the OnePlus 7 Pro (`oneplus-guacamole`, Qualcomm SM8150 / Snapdragon 855). There is no application code and no test suite. "Testing" means building a `boot.img`, booting it on the phone, and checking `dmesg` or the hardware over SSH (`ssh user@172.16.42.1`, USB gadget networking). `docs/PLAN.md` tracks phase status; audio works for stereo speakers and the internal mic (earpiece/call audio still pending). Battery percentage works (fuel gauge). Wi-Fi, Bluetooth, the modem and the charger driver are **not working** yet, even though their firmware and init scripts are packaged.

## Boot image pipeline (actual dev loop)

Device-tree work does **not** go through the upstream `dts/*.dts` sources. The loop is:

1. Edit **`base_guacamole_working.dts`**. This is a *flattened, decompiled* DTS (from `dtc -I dtb -O dts`): no `#include`s, no labels for most nodes, and every cross-reference is a raw numeric phandle (`<0xde>`). When you add a node that others reference, give it a `phandle = <0x...>;` that is unused (grep the file for the current maximum) and reference it numerically.
2. `python3 scripts/patch_dtb.py` applies fix-ups by **exact string replacement** (tab-indented text blocks): it corrects reserved-memory regions, adds the ramoops/bootloader_log/cdsp_sec/param/mtp carve-outs, and injects `qcom,msm-id` / `qcom,board-id` so ABL accepts the DTB. It writes `/tmp/patched_guacamole.dts` and compiles `/tmp/custom_guacamole.dtb`. The `assert` fails if the `rmtfs-mem` block it anchors on is reformatted, so keep that block's exact formatting.
3. `scripts/build_bootimg.sh` runs step 2. It then packs `build/boot.img` (mkbootimg header v2, offsets matching `deviceinfo`, cmdline with ramoops and `PMOS_NO_OUTPUT_REDIRECT`) and adds an AVB hash footer. The kernel comes from `$KERNEL_DIR/boot/vmlinuz` (default `build/kernel_r6`), or failing that from the pmbootstrap chroot at `~/.local/var/pmbootstrap/chroot_rootfs_oneplus-guacamole`. The initramfs comes from `$INITRAMFS` if set, else `/tmp/device_initramfs_r4` or that same chroot.
4. `scripts/flash_boot.sh test` runs `fastboot boot` (non-destructive; prefer this). Do not `fastboot flash boot`. Wrap it in `timeout 10`: the ABL often stalls at `Sending 'boot.img'`, and then the user has to recover the phone by hand. Reboot into the bootloader with `ssh user@172.16.42.1 'sudo reboot bootloader'` (SSH key auth works; `sudo` needs the test password).
5. After a panic, reboot into TWRP and run `scripts/ramoops.sh` to pull pstore logs into `logs/ramoops_<timestamp>/`.

```bash
./scripts/build_bootimg.sh
```

With a new kernel package, the modules in `/lib/modules` on the phone must match the kernel you boot. Install the APK on the phone first (`apk add /tmp/linux-...apk`; this only regenerates `/boot`, it never flashes), extract the same APK into `build/kernel_rN/`, copy the phone's new `/boot/initramfs` next to it, and then run:

```bash
KERNEL_DIR=$PWD/build/kernel_r8 INITRAMFS=$PWD/build/kernel_r8/initramfs ./scripts/build_bootimg.sh
```

```bash
./scripts/flash_boot.sh test
```

Needs on the host: `dtc`, `mkbootimg`, `avbtool`, `fastboot`/`adb` (or `pmbootstrap flasher` as a fallback).

`base_guacamole_working.dts.bak` and `.adsp_only` are untracked manual snapshots from before audio changes. They are not inputs to the build.

## Kernel and packages

- `device/testing/*` are pmaports packages. pmbootstrap builds from `~/.local/var/pmbootstrap/cache_git/pmaports/device/testing/`. The device and firmware packages there are symlinks to this repo, but `linux-postmarketos-qcom-sm8150` is a **separate copy**. After editing the repo copy, copy the files there and run `pmbootstrap checksum`; then make sure both directories are identical (`diff -rq`). Never run two pmbootstrap commands at once: `checksum`/`build` wipe the shared build dir (`chroot_native/home/pmos/build`), which kills a build already in progress. Packages: `device-oneplus-guacamole` (deviceinfo, the charging daemon `guacamole-chgctrl`, the MPSS init script, WoWLAN configs), `firmware-oneplus-guacamole`, and `linux-postmarketos-qcom-sm8150`. The kernel is the `v6.17.0-sm8150` tag from gitlab.com/sm8150-mainline/linux, built with `LLVM=1` and carrying the local `000N-*.patch` files.
- `scripts/build_kernel.sh /path/to/linux` builds a kernel tree via pmbootstrap `envkernel.sh` and then runs `pmbootstrap build --envkernel`. Source `scripts/envsetup.sh` for the `pmb` / `pmb-guacamole` / `envkernel` helpers.
- `pmbootstrap/` is a gitignored clone of pmbootstrap. The pmbootstrap work dir is `~/.local/var/pmbootstrap`.
- Kernel patches: `0004` DSC panel + MSM DSI 2-slices-per-packet, `0005` s6sy761 reset GPIO, `0006` geni I2C FIFO mode, `0007` TFA9874 speaker amp driver (ported from hotdog), `0008` SM8150 `QUATERNARY_MI2S_RX` speaker backend + per-SLIMbus-link channel maps.

## Reference material (untracked, read-only)

- `hotdog-linux-bringup/`: a bringup project for the OnePlus 7T Pro (`hotdog`), a sibling device. Useful for SM8150 patterns, but its hardware differs (for example, touch power on hotdog comes from PM8150L; on guacamole it is PM8150 LDO17 plus GPIO 119).
- `qcom/`: upstream SM8150 audio references (`sm8150-wcd9340.dtsi`, the Xiaomi cepheus/raphael DTS files, the `qdsp6` driver, `sm8150.c` machine driver). Use them as templates when porting audio nodes into the flattened DTS.
- `build/audio_ref/stock_vendor_b/`: stock OxygenOS `tfa98xx.cnt` and `mixer_paths_tavil.xml` read from the phone's `vendor_b` partition. These are the source of truth for audio routes (parse the container with `hotdog-linux-bringup/scripts/inspect-tfa-container.py`).
- `ref/lineageos/`: LineageOS 24 guacamole build (boot/dtbo/vbmeta and the OTA zip). Useful for downstream behaviour, e.g. modem and call audio.
- `linux-v6.17.0-sm8150/`, `build/kernel_r*/`, `extracted_dtb/device.dts` (the live DTB dumped from stock Android via `scripts/extract_dtb.sh`), and `backups/dtbo_*.img`.

## Device-specific gotchas

- Do not enable the PM8150B charger (`charger@1000`) until `qcom_smbx.c` has the SMB5 limit fix (hotdog patch `0020`). Without it, the driver programs about 4.85 V float voltage.
- The fuel gauge is `ti,bq27411` on `i2c@a80000`. Never add `monitored-battery` to it, because that lets the driver write the gauge's data memory.
- ABL splices the UFS `dtbo_<slot>` partition into whatever DTB it boots. The active slot's DTBO has been zeroed (the originals are in `backups/`). If boots hang silently with no early output, check this first.
- The Linux rootfs is a pmOS image on the `userdata` partition (UFS LUN 0, partition 19), with the boot and root subpartitions mounted through `loop0` and referenced by UUID in `/etc/fstab`. Stock Android stays on slot `_b`. `sdX` names are not stable: the six UFS LUNs probe asynchronously, so LUN 0 is not always `sda`. Use `/dev/disk/by-partlabel/` or SCSI addresses (`0:0:0:N`) instead.
- UFS uses 4096-byte sectors (`deviceinfo_rootfs_image_sector_size`).
- Large binaries (`*.img`, the TWRP zip, `stock_boot*.img`) sit in the repo root and are gitignored. Never commit them.
