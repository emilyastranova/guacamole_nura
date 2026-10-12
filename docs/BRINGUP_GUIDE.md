# OnePlus 7 Pro (`oneplus-guacamole`) Mainline Linux & postmarketOS Bring-up

## Device Hardware Overview

| Subsystem | Specification |
| :--- | :--- |
| **SoC** | Qualcomm Snapdragon 855 (`SM8150`, 7nm) |
| **CPU** | 1x Kryo 485 Gold Prime (Cortex-A76 @ 2.84 GHz) + 3x Gold (A76 @ 2.42 GHz) + 4x Silver (Cortex-A55 @ 1.78 GHz) |
| **GPU** | Adreno 640 (`qcom,adreno-640.1`) |
| **Storage** | Samsung 2-lane UFS 3.0 (`/dev/sda` through `/dev/sdf`) |
| **RAM** | LPDDR4X (6GB / 8GB / 12GB) |
| **Display Panel** | Samsung 6.67" 1440x3120 90Hz Curved Fluid AMOLED |
| **DSI Architecture** | Command Mode (DCS) with Display Stream Compression (DSC v1.1, 2 slices/packet) |
| **Touchscreen** | Samsung S6SY761 I2C (`samsung,s6sy761` on `i2c17` / QUPv3 SE 17) |
| **PMIC Architecture**| PM8150 + PM8150B (charger) + PM8150L |

---

## Bootloader DTBO Overlay

### Symptom
Early attempts to boot upstream / mainline kernels (`linux-6.17-sm8150`) stalled before any userspace init or early printk appeared, despite passing valid boot arguments and DTBs inside Android `boot.img`.

### Cause
The OnePlus ABL (Android Bootloader) uses Qualcomm's dynamic device-tree overlay mechanism:
1. When booting from slot `_b`, ABL loads the base DTB from the `boot.img` passed by fastboot.
2. ABL then automatically reads the partition `/dev/block/by-name/dtbo_b` from the internal UFS storage.
3. It traverses vendor DTBO fragments (specifically Qualcomm BSP Android overlays) and attempts to splice them into the in-memory DTB at runtime.
4. Because the mainline SM8150 DTB structure differs significantly from Qualcomm's downstream Android 10/11 kernel DTB, ABL corrupted device tree nodes in RAM, which aborted the boot before any console output.

### Fix
- Zeroed out the active slot's DTBO partition:
  ```bash
  dd if=/dev/zero of=/dev/block/by-name/dtbo_b
  ```
  *(A full raw backup was preserved at `backups/dtbo_b.img` beforehand).*
- Result: ABL passes the mainline DTB through unmodified. The kernel boots through the EFI stub, brings up all 8 CPUs and reaches userspace.

---

## Storage, Partitioning & Preserving Stock Android

### Strategy: Non-Destructive Inactive Slot Usage
The device operates on an A/B dual-slot scheme:
- Stock Android resided on slot `_b` (`system_b`, `boot_b`, `vendor_b`, `userdata`).
- Slot `_a` was inactive. We targeted `/dev/sda13` (`system_a`), leaving slot `_b` intact for stock recovery.

### Storage Layout
Mainline Linux exposes the UFS LUNs as standard SCSI disks:
- `/dev/sda`: Main user data and OS partitions (LUN 0). The `sdX` names are not stable across boots; LUN 0 can enumerate as a later letter.
- `/dev/sdb`: Boot partition 1 / xbl_a (LUN 1)
- `/dev/sdc`: Boot partition 2 / xbl_b (LUN 2)
- `/dev/sdd`: RPMB (LUN 3)
- `/dev/sde` & `/dev/sdf`: Modem, DSP, and firmware pools

### Rootfs Installation
1. Formatted `/dev/sda13` as ext4.
2. Installed a postmarketOS edge rootfs image containing systemd and Phosh.
3. Created loopback device mapping inside initramfs (`/dev/sda13 -> /dev/loop1p2`).
4. Configured USB gadget networking (`rndis` / `cdc_ncm`) giving host IP `172.16.42.2` and device IP `172.16.42.1`.
5. Full mission-mode boot achieved: direct SSH access via `ssh user@172.16.42.1` with active systemd.

---

## Display: SimpleFB vs. Command-Mode DSC

### Why SimpleFB Does Not Update
- In stock Android and bootloader mode, ABL paints an initial splash image (or Tux penguins when kernel boots) into reserved RAM at `0x9c000000`.
- In standard video-mode panels, `simplefb` or `simple-framebuffer` continuously scans out that memory over DSI.
- The OnePlus 7 Pro, however, uses a **Samsung Command Mode (CMD) DSC panel** (`samsung_oneplus_dsc_cmd_display`).
  - Command Mode panels have their own onboard Graphic RAM (GRAM).
  - The display only updates when the host DPU / DSI controller actively fires MIPI DCS write triggers (`MIPI_DSI_DCS_LONG_WRITE`).
  - Once ABL turns over control to the kernel, hardware refreshes cease.
  - Writing to `/dev/fb0` updates host RAM at `0x9c000000`, but without active DPU refresh pulses, the physical panel's GRAM remains unchanged—frozen displaying the boot penguins.

### Native DRM/DPU Driver Stack
To drive this panel, Linux must natively control:
1. **Qualcomm DPU 5.0.0** (`display-controller@ae01000`)
2. **Qualcomm DSI Controller 2.3.0** (`dsi@ae94000`)
3. **Qualcomm 7nm DSI PHY & PLL** (`phy@ae94400`)
4. **Samsung DSC Panel Driver** (`panel-samsung-oneplus-dsc`)

---

## Native Display Driver Architecture & Implementation

### Reference Source
The OnePlus 7T Pro (`hotdog`) community project ([`hotdog-linux-bringup`](file:///home/emily/Documents/Code_Workspace/guacamole_nura/hotdog-linux-bringup)) already supports this display stack on SM8150. Both devices use the same 1440x3120 Samsung AMOLED panel.

### Kernel Patch Components (`0004-drm-msm-enable-native-guacamole-dsc-panel.patch`)

1. **DSI Host Multi-Slice Fix (`drivers/gpu/drm/msm/dsi/dsi_host.c`)**:
   - Upstream MSM DSI assumed `dsc_slice_per_pkt = 1`.
   - The OnePlus panel requires **2 DSC slices per packet** (1440 horizontal pixels divided into two 720-pixel slices transmitted together).
   - Modified timing calculations:
     ```c
     bytes_per_pkt = dsc->slice_chunk_size * msm_host->dsc_slice_per_pkt;
     pkt_per_line = slice_per_intf / msm_host->dsc_slice_per_pkt;
     wc = msm_host->dsc->slice_chunk_size * msm_host->dsc_slice_per_pkt + 1;
     ```
   - Extended `struct drm_dsc_config` with `dsc_slice_per_pkt`.

2. **Samsung DSC Panel Driver (`drivers/gpu/drm/panel/panel-samsung-oneplus-dsc.c`)**:
   - Manages panel power sequencing:
     - `vddio`: PM8150 LDO 14 (`vreg_l14a_1p8`)
     - `avdd`: Dedicated fixed regulator on GPIO 130 (`panel_avdd_1p8`)
     - `reset-gpios`: TLMM GPIO 6 (Active Low)
     - `TE` (Tearing Effect): TLMM GPIO 8 (`mdp_vsync`)
   - Programs hardware DSC PPS (Picture Parameter Set) packets directly into the panel's controller.
   - Exposes both stock **90Hz** (default preferred) and **60Hz** modes with runtime control-display switching (`0x30` for 90Hz, `0x20` for 60Hz).

3. **Guacamole Device Tree (`arch/arm64/boot/dts/qcom/sm8150-oneplus-guacamole.dts`)**:
   - Enabled `&mdss`, `&mdss_mdp`, and `&mdss_dsi0`.
   - Bound `mdss_dsi0_phy` to `vreg_l5a_0p875` and `mdss_dsi0` to `vreg_l3c_1p2`.
   - Configured `panel@0` endpoint linked to `&mdss_dsi0_out` with 4 MIPI data lanes.
   - Removed simplefb nodes from `chosen` and `reserved-memory`.

---

## Build & Packaging Pipeline

- **Kernel Package**: `linux-postmarketos-qcom-sm8150` in `pmaports/device/testing/linux-postmarketos-qcom-sm8150`
- **Configuration**:
  - `CONFIG_DRM_MSM=y`
  - `CONFIG_DRM_MSM_DPU=y`
  - `CONFIG_DRM_MSM_DSI=y`
  - `CONFIG_DRM_MSM_DSI_7NM_PHY=y`
  - `CONFIG_DRM_PANEL_SAMSUNG_ONEPLUS_DSC=y`
- **Boot Generator**: [`scripts/build_bootimg.sh`](file:///home/emily/Documents/Code_Workspace/guacamole_nura/scripts/build_bootimg.sh) packages the compiled kernel `Image.gz` + appended/ramdisk + patched `sm8150-oneplus-guacamole.dtb` into fastboot-bootable format.
