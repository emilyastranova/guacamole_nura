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
| **Storage (UFS)** | :white_check_mark: Working | `ufshcd-qcom` | Capped at HS-G3 (kernel patch `0010`): HS-G4 link errors silently dropped writes; rootfs is a pmOS image on `userdata` |
| **USB Peripheral** | :white_check_mark: Working | `dwc3-qcom` / USB gadget | CDC NCM / RNDIS gadget for SSH (`user@172.16.42.1`) |
| **USB Host (OTG)** | :white_check_mark: Working | `dwc3-qcom` role switch + PM8150B Type-C / VBUS | Dual-role port managed by `qcom,pmic-typec`; a USB thumb drive enumerates at SuperSpeed and mounts in Files. USB gadget/SSH still works when attached to a PC |
| **Battery & Charging** | :construction: WIP | `bq27411` gauge + PM8150B SMB5 charger | Percentage, charging and plugged-in state work (4.35 V / 1.5 A, kernel patches `0011`, `0012`); charge-limit daemon and wall-charger charging are WIP |
| **Auto-rotate** | :x: Not Working | SLPI sensor DSP (SSC) | Accelerometer is behind the sensor DSP; see "Sensors" in `docs/PLAN.md` |
| **Brightness Sensor** | :x: Not Working | SLPI sensor DSP (SSC) | Ambient light sensor is behind the sensor DSP, like the accelerometer; see "Sensors" in `docs/PLAN.md` |
| **Camera** | :x: Not Working | SM8150 CAMSS / CCI | Not started; see "Camera" in `docs/PLAN.md` |
| **Volume Keys** | :white_check_mark: Working | `gpio-keys` (PM8150 GPIO 6/7) | Volume up/down report `KEY_VOLUMEUP`/`KEY_VOLUMEDOWN` |
| **GPU Acceleration** | :white_check_mark: Working | Adreno 640 / Mesa Freedreno & Turnip | GMU v2.0.261 + ZAP shader loaded; native OpenGL ES 3.2 and Vulkan 1.3 |
| **Wi-Fi** | :white_check_mark: Working | `ath10k_snoc` (WCN3990) | 2.4 and 5 GHz, DHCP and internet; OxygenOS 12-era WLAN firmware + kernel patch `0009`. Rebooting with Wi-Fi on can enter Qualcomm crashdump mode (see below). Stable MAC and WoWLAN pending |
| **Bluetooth** | :white_check_mark: Working | `hci_qca` (WCN3990) on UART13 | Scanning and HID devices; stable address from the factory Wi-Fi MAC; audio profiles untested |
| **Modem / MPSS** | :construction: DSP running | Hexagon remoteproc / PAS | Modem DSP runs and hosts the WLAN firmware; cellular (ModemManager, SIM, calls, data) not working; see "Wi-Fi, Bluetooth & Modem Bringup" in `docs/PLAN.md` |
| **Audio** | :white_check_mark: Speakers & Mic | QDSP6 ADSP + 2x NXP TFA9874 (QUAT MI2S) + WCD9340 (SLIMbus) | Stereo speakers and internal mic working via UCM2; earpiece/call audio and speaker protection pending |

---

## Hardware Notes

### Bootloader DTBO Overlay
Stock OnePlus ABL automatically reads `/dev/block/by-name/dtbo_[slot]` from internal UFS and dynamically splices vendor Android DTBO fragments into the in-memory device tree passed by fastboot. The mainline DTB layout differs from the downstream Android kernel's, so the overlay corrupts nodes and the boot hangs with no output. Zeroing the active slot's `dtbo` partition stops ABL from applying the overlay.

### Native Samsung Command-Mode DSC Display Driver
The OnePlus 7 Pro uses a high-density 1440x3120 90Hz Samsung AMOLED panel requiring **Command Mode (DCS)** and **Display Stream Compression (DSC v1.1)** with **2 slices per packet** (two 720-pixel slices transmitted together). Because Command Mode panels only update their internal Graphic RAM when the host DPU fires DCS write triggers, SimpleFB remains frozen. The `panel-samsung-oneplus-dsc` driver and a patch to the MSM DSI host timing calculations drive the panel at 90 Hz through the MSM DPU.

### Touchscreen Power Rail Routing
The `s6sy761` digitizer IC on the OnePlus 7 Pro is powered by **PM8150 LDO 17** (`vreg_l17a_3p0`, 3.0V), unlike the OnePlus 7T Pro which uses PM8150L. Additionally, GPIO 119 (`tp-1v8-active`) must be driven HIGH to enable the 1.8V digital rail. With both supplies configured, the controller probes at address `0x48` and reports multi-touch events on `/dev/input/event1`.

### Speaker Amplifiers
The loudspeakers are not driven by the WCD9340 codec. Two NXP TFA9874 amplifiers (I2C `0x34` top/earpiece, `0x35` bottom, on `i2c@890000`) receive audio over `QUATERNARY_MI2S_RX` at S24_LE, 48 kHz. Their register profile matches the stock `/vendor/firmware/tfa98xx.cnt`. The WCD9340 on SLIMbus handles the microphones.

### Crashdump on Reboot with Wi-Fi On
> [!WARNING]
> Rebooting while the Wi-Fi radio is on can drop the phone into Qualcomm crashdump mode instead of rebooting. Recover with Power + Volume Up. Until this is fixed, switch the radio off before every reboot or shutdown:
>
> ```bash
> sudo nmcli radio wifi off
> ```

The modem DSP hosts the WLAN firmware, and while Wi-Fi is active the MSA memory region is assigned to the modem. Mainline does not reclaim that assignment before the modem stops, which is the suspected cause. Reboots with the radio off have gone straight to fastboot every time so far. Investigation notes are under "Crashdump on reboot" in `docs/PLAN.md`.

### Wi-Fi and Bluetooth Firmware Source
> [!NOTE]
> The WCN3990 Wi-Fi firmware (`wlanmdsp.mbn`, `WLAN.HL.3.0.c8`), its board data (`board-2.bin`) and the Bluetooth firmware (`crbtfw21.tlv`, `crnv21.bin`) are currently extracted from a LineageOS 24 OTA with `scripts/extract_lineage_firmware.py`. The extraction step creates a local, gitignored tarball that `firmware-oneplus-guacamole` builds from, so the package cannot yet be built from public URLs alone. The modem itself still uses the OxygenOS 11 build.

The public firmware in [sm8150-mainline/firmware-oneplus-sm8150](https://gitlab.com/sm8150-mainline/firmware-oneplus-sm8150) (`WLAN.HL.3.2.0`) failed station `vdev start` in earlier testing. That testing ran before the UFS HS-G3 cap, while the HS-G4 link was silently dropping writes, so the firmware files or rootfs may have been corrupted. Those results need to be repeated before ruling the GitLab firmware out. That repository carries no Bluetooth firmware; `linux-firmware` ships `qca/crbtfw21.tlv` and `qca/crnv21.bin` and is the public candidate for Bluetooth.

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
    ├── PLAN.md                     # Bringup roadmap and status
    └── BRINGUP_GUIDE.md            # Hardware notes and bringup walkthrough
```

---

## Current Roadmap: Next Focus

- [ ] **Audio follow-ups** (see "Remaining audio work" in `docs/PLAN.md`):
  - Earpiece "receiver" profile and call audio routing.
  - Secondary microphones, speaker protection and default volume limits.
  - Settle on one sound server (PulseAudio vs PipeWire).
- [ ] **Wi-Fi, Bluetooth & Modem Bringup** (see "Wi-Fi, Bluetooth & Modem Bringup" in `docs/PLAN.md`):
  - (WIP) Re-test the sm8150-mainline GitLab Wi-Fi firmware (and the `linux-firmware` Bluetooth files) now that UFS writes are reliable; earlier failures may have come from storage corruption. If they work, drop the LineageOS extraction step.
  - Give `wlan0` a stable MAC address and test WoWLAN.
  - Validate SIM, SMS, mobile data and calls via ModemManager.
- [ ] **Auto-rotate** (see "Sensors" in `docs/PLAN.md`).
- [ ] **Brightness sensor** (see "Sensors" in `docs/PLAN.md`).
- [ ] **Camera** (see "Camera" in `docs/PLAN.md`).
- [ ] **Battery & Charging** (see "Battery & Charging" in `docs/PLAN.md`):
  - (WIP) Rework `guacamole-chgctrl.daemon` for the `bq27411-0` gauge and mainline charger controls.
  - (WIP) Validate wall-charger (DCP) charging and thermals before raising the 1.5 A limit.