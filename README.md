# Nura for OnePlus 7 Pro (`oneplus-guacamole`)

[![Target SoC: Snapdragon 855](https://img.shields.io/badge/SoC-Qualcomm%20SM8150-blue.svg)](https://wiki.nura.eco/wiki/Qualcomm_Snapdragon_855_(SM8150))
[![Platform: Nura / postmarketOS](https://img.shields.io/badge/Platform-Nura%20(postmarketOS)-brightgreen.svg)](https://wiki.nura.eco)
[![Architecture: aarch64](https://img.shields.io/badge/Arch-aarch64-orange.svg)](https://wiki.nura.eco/wiki/Category:Aarch64)

This repository contains the bringup workspace, device package definitions, device trees, firmware packages, helper utilities, and documentation for porting **Nura** (formerly [postmarketOS](https://postmarketos.org)) to the **OnePlus 7 Pro** (codename `guacamole`).

---

## Device Specifications

| Attribute | Value |
| :--- | :--- |
| **Model** | OnePlus 7 Pro (`GM1910`, `GM1911`, `GM1913`, `GM1917`, etc.) |
| **Codename** | `guacamole` (`oneplus-guacamole`) |
| **Chipset** | Qualcomm Snapdragon 855 (`SM8150`) |
| **CPU** | 8-core Kryo 485 (1x 2.84 GHz + 3x 2.42 GHz + 4x 1.78 GHz) |
| **GPU** | Qualcomm Adreno 640 |
| **Display** | 6.67" Fluid AMOLED, 3120x1440 (19.5:9), 90Hz |
| **Touchscreen** | Samsung `s6sy761` I2C Touchscreen (`&i2c17` @ `0x48`) |
| **Storage** | 128 GB / 256 GB UFS 3.0 (4096-byte sector size) |
| **RAM** | 6 GB / 8 GB / 12 GB LPDDR4X |
| **Partition Scheme** | Standard Android A/B slot system (No dynamic "super" partition) |
| **Flash Method** | Android Fastboot (`fastboot boot` / `fastboot flash`) |

---

## Hardware Support Status

| Subsystem | Status | Driver / Implementation | Notes |
| :--- | :---: | :--- | :--- |
| **Bootloader** | :white_check_mark: Working | Qualcomm ABL | Unlocked bootloader supports `fastboot boot` |
| **Display (Splash)** | :white_check_mark: Working | `simple-framebuffer` | Handed off from bootloader `0x9C000000` |
| **Crash Logging** | :white_check_mark: Working | `pstore` / `ramoops` | Captures kernel panics across warm reboots |
| **Device Tree** | :white_check_mark: Integrated | `sm8150-oneplus-guacamole.dts` | Mainline DTS by Caleb Connolly |
| **Touchscreen** | :white_check_mark: Configured | `samsung,s6sy761` | Bound to `&i2c17` at `0x48` in DTS |
| **Storage (UFS)** | :construction: In Progress | `ufshcd-qcom` | Requires 4096 sector size configuration |
| **USB Peripheral** | :construction: In Progress | `dwc3-qcom` / `gadget` | USB Type-C OTG and USB Ethernet for SSH |
| **Charging Control** | :white_check_mark: Integrated | `guacamole-chgctrl.daemon` | Charging management daemon & init service |
| **GPU Acceleration** | :construction: In Progress | Freedreno / Turnip (`card0`) | ZAP shader packaged in `firmware-oneplus-guacamole` |
| **Wi-Fi** | :construction: In Progress | `ath10k_snoc` (WCN3990) | Board data & WoWLAN rules integrated |
| **Modem / MPSS** | :construction: In Progress | Hexagon remoteproc / PAS | `guacamole-mpss.initd` service integrated |
| **Audio** | :hourglass_flowing_sand: Planned | Hexagon QDSP6 | ALSA / PipeWire via ADSP |

---

## Repository Structure

```
guacamole_nura/
├── .gitignore                      # Git ignore rules for build trees and blobs
├── README.md                       # Project documentation and quickstart
├── pmbootstrap/                    # Cloned pmbootstrap source repository
│
├── device/                         # Nura / postmarketOS package recipes
│   └── testing/
│       ├── device-oneplus-guacamole/
│       │   ├── APKBUILD            # Device package definition with OpenRC subpackage
│       │   ├── deviceinfo          # Bootimg parameters, screen resolution, offsets
│       │   ├── guacamole-chgctrl.* # Battery charging daemon, init script & conf
│       │   ├── guacamole-mpss.initd# MPSS modem bringup service
│       │   ├── 90-wifi-wowlan.conf # NetworkManager WoWLAN profile
│       │   ├── 90-ath10k-wowlan.rules # Udev wake-on-WLAN rules
│       │   ├── 10-wifi-wowlan      # Dispatcher script for WiFi wake
│       │   └── sxmo_deviceprofile* # Sxmo button profile
│       ├── firmware-oneplus-guacamole/
│       │   ├── APKBUILD            # GPU zap shader, WCN3990 & modem firmware package
│       │   └── 30-gpu-firmware.files # Initramfs early GPU firmware loader config
│       └── linux-postmarketos-qcom-sm8150/
│           ├── APKBUILD            # SM8150 mainline kernel package recipe
│           ├── config-postmarketos-qcom-sm8150.aarch64 # Kernel Kconfig
│           └── *.patch             # Hardware patches (UFS, LID, LLVM)
│
├── dts/                            # Upstream device tree sources
│   ├── sm8150-oneplus-guacamole.dts# Official OnePlus 7 Pro devicetree
│   └── sm8150-oneplus-common.dtsi  # Shared OnePlus 7 series SoC dtsi
│
├── firmware/                       # Firmware documentation and extraction tools
│   └── README.md                   # OTA payload firmware dumping guide
│
├── scripts/                        # Automated development utilities
│   ├── envsetup.sh                 # Environment setup and aliases
│   ├── extract_dtb.sh              # ADB tool to extract & decompile live DTB
│   ├── build_kernel.sh             # Compiles kernel using envkernel.sh
│   ├── flash_boot.sh               # Non-destructive fastboot testing helper
│   └── ramoops.sh                  # Dumps pstore logs following kernel panic
│
└── docs/                           # Detailed technical documentation
    └── PLAN.md                     # Comprehensive bringup roadmap & status
```

---

## Getting Started

### 1. Prerequisites

Ensure your host system (Linux) has the necessary utilities:
- Python 3.10+
- `fastboot` and `adb` (from `android-tools`)
- `dtc` (device-tree-compiler)
- Git and OpenSSL

### 2. Initialize Development Environment

Source the environment script to register aliases and set path variables:
```bash
source scripts/envsetup.sh
```

### 3. Configure `pmbootstrap`

Initialize pmbootstrap for your environment:
```bash
pmbootstrap init
```
When prompted:
- **Work path**: `~/.local/var/pmbootstrap`
- **Channel**: `edge`
- **Vendor**: `oneplus`
- **Device**: `guacamole`
- **Kernel**: `postmarketos-qcom-sm8150`
- **User Interface**: `phosh` (or `sxmo` / `console`)

Link your local device packages into pmbootstrap's aports tree:
```bash
APORTS="$(pmbootstrap -q config aports)"
ln -s "$(pwd)/device/testing/device-oneplus-guacamole" "$APORTS/device/testing/device-oneplus-guacamole"
ln -s "$(pwd)/device/testing/firmware-oneplus-guacamole" "$APORTS/device/testing/firmware-oneplus-guacamole"
ln -s "$(pwd)/device/testing/linux-postmarketos-qcom-sm8150" "$APORTS/device/testing/linux-postmarketos-qcom-sm8150"
```

---

## Development Workflow

### Step 1: Build Packages with `pmbootstrap`

Build the kernel and firmware packages:
```bash
pmbootstrap build linux-postmarketos-qcom-sm8150
pmbootstrap build firmware-oneplus-guacamole
pmbootstrap build device-oneplus-guacamole
```

### Step 2: Test Booting (Non-destructive)

To test a newly built kernel without overwriting your phone's storage:
1. Put the OnePlus 7 Pro into Fastboot mode (`Power` + `Volume Down`).
2. Run the boot test helper:
   ```bash
   ./scripts/flash_boot.sh test
   ```
   This executes `fastboot boot boot.img`, streaming the image directly to RAM.

### Step 3: Debugging Panics with Ramoops

If the device hangs or reboots into the bootloader:
1. Boot into TWRP or an alternative functional recovery kernel.
2. Run the ramoops helper:
   ```bash
   ./scripts/ramoops.sh
   ```
3. Inspect `logs/ramoops_*/` for panic traces and stack traces.

---

## Key References & Upstream Projects

- [OnePlus 7 Pro Nura Wiki](https://wiki.nura.eco/wiki/OnePlus_7_Pro_(oneplus-guacamole))
- [SM8150 Mainline Linux Kernel (`sm8150/6.17`)](https://gitlab.postmarketos.org/soc/qualcomm-sm8150/linux)
- [M1DNYT3 pmaports branch](https://gitlab.postmarketos.org/M1DNYT3/pmaports/-/tree/device-oneplus-guacamole)
- [Caleb Connolly's Qualcomm Mainline Contributions](https://gitlab.postmarketos.org/soc/qualcomm-sm8150/linux/-/commits/sm8150/6.17)
- [Full Bringup Plan](file:///home/emily/Documents/Code_Workspace/guacamole_nura/docs/PLAN.md)
