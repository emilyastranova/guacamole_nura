# Nura for OnePlus 7 Pro (`oneplus-guacamole`)

[![Target SoC: Snapdragon 855](https://img.shields.io/badge/SoC-Qualcomm%20SM8150-blue.svg)](https://wiki.nura.eco/wiki/Qualcomm_Snapdragon_855_(SM8150))
[![Platform: Nura / postmarketOS](https://img.shields.io/badge/Platform-Nura%20(postmarketOS)-brightgreen.svg)](https://wiki.nura.eco)
[![Architecture: aarch64](https://img.shields.io/badge/Arch-aarch64-orange.svg)](https://wiki.nura.eco/wiki/Category:Aarch64)

This repository contains the bringup workspace, device package definitions, device trees, helper utilities, and documentation for porting **Nura** (formerly [postmarketOS](https://postmarketos.org)) to the **OnePlus 7 Pro** (codename `guacamole`).

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
| **Storage** | 128 GB / 256 GB UFS 3.0 (4096-byte sector size) |
| **RAM** | 6 GB / 8 GB / 12 GB LPDDR4X |
| **Partition Scheme** | Standard Android A/B slot system (No dynamic "super" partition) |
| **Flash Method** | Android Fastboot (`fastboot boot` / `fastboot flash`) |

> [!NOTE]
> Unlike the OnePlus 7T / 7T Pro (`hotdog`) series which introduced Android dynamic "Super" partitions, the OnePlus 7 and 7 Pro use traditional individual slot partitions (`boot_a`, `system_a`, `vendor_a`, etc.), simplifying flashing and testing.

---

## Hardware Support Status

| Subsystem | Status | Driver / Implementation | Notes |
| :--- | :---: | :--- | :--- |
| **Bootloader** | :white_check_mark: Working | Qualcomm ABL | Unlocked bootloader supports `fastboot boot` |
| **Display (Splash)** | :white_check_mark: Working | `simple-framebuffer` | Handed off from bootloader `cont_splash_region` |
| **Crash Logging** | :white_check_mark: Working | `pstore` / `ramoops` | Captures kernel panics across warm reboots |
| **Storage (UFS)** | :construction: In Progress | `ufshcd-qcom` | Requires 4096 sector size configuration |
| **USB Peripheral** | :construction: In Progress | `dwc3-qcom` / `gadget` | USB Type-C OTG and USB Ethernet for SSH |
| **Hardware Keys** | :construction: In Progress | `gpio-keys` / `pm8150-pon` | Power and Volume keys |
| **Display (Native DSI)** | :hourglass_flowing_sand: Planned | DRM DSI panel driver | Samsung 90Hz AMOLED panel |
| **3D Acceleration** | :hourglass_flowing_sand: Planned | Freedreno DRM / Turnip | Adreno 640 GPU with `a640_zap.mbn` |
| **Touchscreen** | :hourglass_flowing_sand: Planned | Synaptics / Goodix I2C | Digitizer bringup in devicetree |
| **Wi-Fi** | :warning: Known Issue | `ath10k_snoc` (WCN3990) | Firmware crash observed with stock OTA blobs |
| **Bluetooth** | :hourglass_flowing_sand: Planned | `hci_qca` | WCN3990 over UART |
| **Modem / Telephony** | :warning: Known Issue | Hexagon remoteproc / PAS | Non-functional with stock OTA firmware; under debug |
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
│       │   ├── APKBUILD            # Device package definition
│       │   └── deviceinfo          # Bootimg parameters, screen resolution, offsets
│       └── linux-postmarketos-qcom-sm8150/
│           ├── APKBUILD            # SM8150 mainline kernel package recipe
│           ├── config-postmarketos-qcom-sm8150.aarch64 # Kernel Kconfig
│           └── *.patch             # Hardware patches (UFS, LID, LLVM)
│
├── dts/                            # Device tree sources
│   └── sm8150-oneplus-guacamole.dts# OnePlus 7 Pro devicetree template
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
    └── PLAN.md                     # Comprehensive multi-phase bringup roadmap
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
- **User Interface**: `phosh` (or `console` for early bringup)

Link your local device packages into pmbootstrap's aports tree:
```bash
APORTS="$(pmbootstrap -q config aports)"
ln -s "$(pwd)/device/testing/device-oneplus-guacamole" "$APORTS/device/testing/device-oneplus-guacamole"
ln -s "$(pwd)/device/testing/linux-postmarketos-qcom-sm8150" "$APORTS/device/testing/linux-postmarketos-qcom-sm8150"
```

---

## Development Workflow

### Step 1: Extract Downstream Device Tree

Boot your OnePlus 7 Pro into stock Android (or TWRP) with ADB enabled, then run:
```bash
./scripts/extract_dtb.sh
```
This pulls `/sys/firmware/fdt` and decompiles it into `extracted_dtb/device.dts`.
Inspect `extracted_dtb/device.dts` to verify:
1. `qcom,board-id` and `qcom,msm-id` values.
2. `cont_splash_region` base address and length for SimpleFB.
3. Reserved memory addresses to compare against `sm8150.dtsi`.

### Step 2: Compile the Kernel with `envkernel`

Using `pmbootstrap`'s `envkernel.sh` allows rapid cross-compilation directly in a kernel source directory:
```bash
# Clone the SM8150 mainline kernel branch:
git clone --depth=1 https://gitlab.com/sm8150-mainline/linux.git ../linux-sm8150

# Compile and package:
./scripts/build_kernel.sh ../linux-sm8150
```

### Step 3: Test Booting (Non-destructive)

To test a newly compiled kernel without overwriting your phone's storage:
1. Put the OnePlus 7 Pro into Fastboot mode (`Power` + `Volume Down`).
2. Run the boot test helper:
   ```bash
   ./scripts/flash_boot.sh test
   ```
   This executes `fastboot boot boot.img`, streaming the image directly to RAM.

### Step 4: Debugging Panics with Ramoops

If the device hangs or reboots into the bootloader:
1. Boot into TWRP or an alternative functional recovery kernel.
2. Run the ramoops helper:
   ```bash
   ./scripts/ramoops.sh
   ```
3. Inspect `logs/ramoops_*/` for panic traces and stack traces.

---

## Key Hardware Quirks & Notes

### SM8150 Mainline vs SM7150
While the OnePlus 7 Pro porting guide references the [SM7150 Mainlining Guide](https://wiki.nura.eco/wiki/SM7150_Mainlining), remember:
- The OnePlus 7 Pro uses **SM8150** (Snapdragon 855), not SM7150 (Snapdragon 730).
- Compatible strings must target `qcom,sm8150`.
- Upstream devicetree base is `arch/arm64/boot/dts/qcom/sm8150.dtsi`.

### Protected GPIO Pins
To prevent TrustZone / Qualcomm Hypervisor crashes, ensure protected GPIO pins (monitored for fingerprint and secure elements) are reserved in the device tree:
```dts
&tlmm {
    gpio-reserved-ranges = <0 4>, <59 4>;
};
```

### UFS 3.0 Storage
Because the device uses UFS storage, Alpine / Nura images must be generated with a 4096-byte sector size:
```sh
deviceinfo_rootfs_image_sector_size="4096"
```

---

## References & Documentation

- [OnePlus 7 Pro Nura Wiki](https://wiki.nura.eco/wiki/OnePlus_7_Pro_(oneplus-guacamole))
- [SM7150 Mainlining Guide (Reference)](https://wiki.nura.eco/wiki/SM7150_Mainlining#Build_Kernel)
- [Nura Porting to a New Device](https://wiki.nura.eco/wiki/Porting_to_a_new_device)
- [PostmarketOS pmaports device-oneplus-guacamole](https://gitlab.postmarketos.org/postmarketOS/pmaports/-/tree/main/device/testing/device-oneplus-guacamole)
- [SM8150 Mainline Linux Kernel](https://gitlab.com/sm8150-mainline/linux)
- [Full Bringup Plan](file:///home/emily/Documents/Code_Workspace/guacamole_nura/docs/PLAN.md)
