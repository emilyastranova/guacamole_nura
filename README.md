# Nura for OnePlus 7 Pro (`oneplus-guacamole`)

[![Target SoC: Snapdragon 855](https://img.shields.io/badge/SoC-Qualcomm%20SM8150-blue.svg)](https://wiki.nura.eco/wiki/Qualcomm_Snapdragon_855_(SM8150))
[![Platform: Nura / postmarketOS](https://img.shields.io/badge/Platform-Nura%20(postmarketOS)-brightgreen.svg)](https://wiki.nura.eco)
[![Architecture: aarch64](https://img.shields.io/badge/Arch-aarch64-orange.svg)](https://wiki.nura.eco/wiki/Category:Aarch64)

This repository contains the bringup workspace, kernel patches, device tree sources, firmware packages, helper utilities, and documentation for running **postmarketOS / Nura** on the **OnePlus 7 Pro** (codename `guacamole`).

---

## Device Specifications

| Attribute | Value |
| :--- | :--- |
| **Model** | OnePlus 7 Pro (`GM1910`, `GM1911`, `GM1913`, `GM1917`, etc.) |
| **Codename** | `guacamole` (`oneplus-guacamole`) |
| **Chipset** | Qualcomm Snapdragon 855 (`SM8150`) |
| **CPU** | 8-core Kryo 485 (1x 2.84 GHz Prime + 3x 2.42 GHz Gold + 4x 1.78 GHz Silver) |
| **GPU** | Qualcomm Adreno 640 (`qcom,adreno-640.1`) |
| **Display** | 6.67" Curved Fluid AMOLED, 3120x1440 (19.5:9), 90Hz Command-Mode DSC |
| **Touchscreen** | Samsung `s6sy761` I2C Touchscreen (`&i2c17` @ `0x48`) |
| **Storage** | 128 GB / 256 GB UFS 3.0 (`/dev/sda` through `/dev/sdf`) |
| **RAM** | 6 GB / 8 GB / 12 GB LPDDR4X |
| **Partition Scheme** | Standard Android A/B slot system (non-super) |
| **Access Method** | USB Ethernet Gadget (`172.16.42.1`) + Wayland/Phosh GUI |

---

## Hardware Support Status

| Subsystem | Status | Driver / Implementation | Notes |
| :--- | :---: | :--- | :--- |
| **Bootloader (ABL)** | :white_check_mark: Working | Qualcomm ABL | Unlocked ABL; active slot `dtbo` zeroed to prevent downstream overlay corruption |
| **Display (DRM/KMS)** | :white_check_mark: Working | `panel-samsung-oneplus-dsc` + MSM DPU/DSI | Native 3120x1440 @ 90Hz Command-Mode DSC with 2 slices/packet |
| **Touchscreen** | :white_check_mark: Working | `samsung,s6sy761` on `&i2c17` (`0x48`) | Powered via PM8150 `ldo17` (3.0V) + GPIO 119 1.8V rail pull-up |
| **Storage (UFS)** | :white_check_mark: Working | `ufshcd-qcom` | Dual-lane UFS 3.0 mounted at `/dev/sda`; rootfs installed on `/dev/sda13` |
| **USB Peripheral** | :white_check_mark: Working | `dwc3-qcom` / USB gadget | USB Type-C OTG + CDC NCM / RNDIS gadget for SSH (`user@172.16.42.1`) |
| **Battery & Charging** | :x: Not Working | Fuel gauge @ `0x55` + PM8150B charger | Reads 0% while plugged in; fuel gauge node missing, charger disabled in DTS (Phase 10) |
| **GPU Acceleration** | :white_check_mark: Working | Adreno 640 / Mesa Freedreno & Turnip | GMU v2.0.261 + ZAP shader loaded; native OpenGL ES 3.2 and Vulkan 1.3 |
| **Wi-Fi** | :x: Not Working | `ath10k_snoc` (WCN3990) | Board data & WoWLAN rules packaged; bringup pending (Phase 9) |
| **Bluetooth** | :x: Not Working | `hci_qca` (WCN3990) | Not yet enabled (Phase 9) |
| **Modem / MPSS** | :x: Not Working | Hexagon remoteproc / PAS | Firmware & `guacamole-mpss.initd` packaged; bringup pending (Phase 9) |
| **Steam & Gaming** | :white_check_mark: Working | Native ARM64 Steam + FEX-Emu + Proton | Turnip Vulkan thunking, pressure-vessel container integration |
| **Audio** | :white_check_mark: Speakers & Mic | QDSP6 ADSP + 2x NXP TFA9874 (QUAT MI2S) + WCD9340 (SLIMbus) | Stereo speakers and internal mic working via UCM2; earpiece/call audio and speaker protection pending |

---

## Key Breakthroughs & Architecture Notes

### 1. The Bootloader DTBO Discovery
Stock OnePlus ABL automatically reads `/dev/block/by-name/dtbo_[slot]` from internal UFS and dynamically splices vendor Android DTBO fragments into the in-memory device tree passed by fastboot. Because mainline DTB hierarchy differs fundamentally from downstream Android kernels, this corrupted device tree nodes in RAM, producing silent boot freezes. Zeroing the active slot's `dtbo` partition allowed the clean mainline DTB to pass untouched.

### 2. Native Samsung Command-Mode DSC Display Driver
The OnePlus 7 Pro uses a high-density 1440x3120 90Hz Samsung AMOLED panel requiring **Command Mode (DCS)** and **Display Stream Compression (DSC v1.1)** with **2 slices per packet** (two 720-pixel slices transmitted together). Because Command Mode panels only update their internal Graphic RAM when the host DPU fires DCS write triggers, SimpleFB remains frozen. We integrated the native `panel-samsung-oneplus-dsc` driver and patched MSM DSI host timing calculations, achieving smooth 90Hz hardware-accelerated display rendering.

### 3. Touchscreen Power Rail Routing
The `s6sy761` digitizer IC on the OnePlus 7 Pro is powered by **PM8150 LDO 17** (`vreg_l17a_3p0`, 3.0V), unlike the OnePlus 7T Pro which uses PM8150L. Additionally, GPIO 119 (`tp-1v8-active`) must be driven HIGH to enable the 1.8V digital rail. Configuring both supplies enables immediate probing at address `0x48` with full multi-touch reporting on `/dev/input/event1`.

### 4. Native ARM64 Steam Client & Gaming Layer
Rather than emulating the entire x86_64 Steam client under FEX-Emu (which deadlocks on Chromium CEF sandbox thread/zombie waitpid handling), Valve's native ARM64 Linux Steam client runs natively in an Ubuntu 24.04 container (`steam-box`) via Distrobox.
- **Vulkan Driver**: Host Turnip Vulkan Adreno 640 mapped into containers.
- **Emulation**: FEX-Emu translates x86_64 game binaries with Vulkan thunking.
- **Proton**: Proton Experimental runs Windows binaries via Wine with VKD3D-Proton translating DirectX 12 to Vulkan.

---

## Repository Structure

```
guacamole_nura/
├── README.md                       # Main project documentation and status
├── base_guacamole_working.dts      # Active working device tree source for OnePlus 7 Pro
├── pmbootstrap/                    # pmbootstrap source repository
│
├── device/                         # Nura / postmarketOS package recipes
│   └── testing/
│       ├── device-oneplus-guacamole/
│       │   ├── APKBUILD            # Device package definition with OpenRC/systemd subpackages
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
│           └── *.patch             # Hardware patches (DSC panel, UFS, LID, LLVM)
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
    ├── PLAN.md                     # Comprehensive bringup roadmap & status
    └── BRINGUP_GUIDE.md            # Hardware notes and bringup walkthrough
```

---

## Current Roadmap: Next Focus

- [ ] **Audio follow-ups** (see `docs/PLAN.md` Step 8.7):
  - Earpiece "receiver" profile and call audio routing.
  - Secondary microphones, speaker protection and default volume limits.
  - Settle on one sound server (PulseAudio vs PipeWire).
- [ ] **Wi-Fi, Bluetooth & Modem Bringup** (see `docs/PLAN.md` Phase 9):
  - Bring up the MPSS modem remoteproc with `rmtfs`, `pd-mapper` and `tqftpserv`.
  - Get WCN3990 Wi-Fi (`ath10k_snoc`) probing and associating.
  - Enable WCN3990 Bluetooth (`hci_qca`) and package its firmware.
  - Validate SIM, SMS, mobile data and calls via ModemManager.
- [ ] **Battery & Charging** (see `docs/PLAN.md` Phase 10):
  - Add the fuel gauge node at I2C `0x55` (likely `ti,bq27411` register layout, as on the 7T Pro).
  - Enable the PM8150B charger and fix `guacamole-chgctrl.daemon` power-supply paths.
