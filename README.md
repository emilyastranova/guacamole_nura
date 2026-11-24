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
| **Battery & Charging** | :construction: WIP | `bq27411` gauge + PM8150B SMB5 charger + `guacamole-chgctrl` | Percentage, charging and plugged-in state work (4.35 V / 3 A, kernel patches `0011`, `0012`, `0018`, `0019`); charge policy daemon sets the input limit from the USB-PD contract, DCP 1.8 A, thermal throttling and an optional charge window, and reports the source type; DCP (5 V/1.8 A) and USB-PD 5 V/3 A (15 W) verified; 9 V PD negotiates (kernel patches `0020`–`0024`) but the board never passes 9 V to the PMIC, so 15 W is the ceiling; Warp Charge unsupported |
| **Auto-rotate** | :white_check_mark: Working | SLPI sensor DSP (SSC) + `hexagonrpcd` + `iio-sensor-proxy` | LSM6DSM accelerometer through the sensor DSP (kernel patch `0017`, SLPI firmware, patched `hexagonrpcd`/`iio-sensor-proxy`, udev mount matrix); Phosh rotates, verified across reboots; see "Sensors" in `docs/PLAN.md` |
| **Brightness Sensor** | :white_check_mark: Working | SLPI sensor DSP (SSC) + `iio-sensor-proxy` | TCS3701 light sensor; Phosh automatic brightness works with `ambient-enabled` set to true (off by default); proximity reports but is untested |
| **Camera** | :construction: Rear cameras | SM8150 CAMSS + CCI, `imx586`/`s5k3m5`/`imx481`, `lc898217xc` actuators, libcamera software ISP | Main, telephoto and ultra-wide capture RAW10 at 30 fps and through libcamera (kernel patches `0025`–`0047`); PM8150L flash works as a torch; the pop-up front IMX471 does not answer on this unit; see "Cameras" below and in `docs/PLAN.md` |
| **Volume Keys** | :white_check_mark: Working | `gpio-keys` (PM8150 GPIO 6/7) | Volume up/down report `KEY_VOLUMEUP`/`KEY_VOLUMEDOWN` |
| **GPU Acceleration** | :white_check_mark: Working | Adreno 640 / Mesa Freedreno & Turnip | GMU v2.0.261 + ZAP shader loaded; native OpenGL ES 3.2 and Vulkan 1.3 |
| **Wi-Fi** | :white_check_mark: Working | `ath10k_snoc` (WCN3990) | 2.4 and 5 GHz, DHCP and internet; OxygenOS 12-era WLAN firmware + kernel patch `0009`. Factory MAC as the interface address; NetworkManager uses a stable per-network MAC when connected. WoWLAN pending |
| **Bluetooth** | :white_check_mark: Working | `hci_qca` (WCN3990) on UART13 | Scanning and HID devices; stable address from the factory Wi-Fi MAC; audio profiles untested |
| **Modem / MPSS** | :construction: Detected | Hexagon remoteproc / PAS + IPA v4.1 (`rmnet_ipa0`) | ModemManager detects the modem (QMI over QRTR, IPA data path, kernel patches `0013`–`0016`); SIM, registration, data and calls untested, no SIM fitted yet; see "Wi-Fi, Bluetooth & Modem Bringup" in `docs/PLAN.md` |
| **Audio** | :white_check_mark: Speakers (Mic WIP) | QDSP6 ADSP + 2x NXP TFA9874 (QUAT MI2S) | Stereo speakers verified at full volume via PipeWire/WirePlumber S16LE override; internal mic and call audio pending |

---

## Hardware Notes

### Bootloader DTBO Overlay
Stock OnePlus ABL automatically reads `/dev/block/by-name/dtbo_[slot]` from internal UFS and dynamically splices vendor Android DTBO fragments into the in-memory device tree passed by fastboot. The mainline DTB layout differs from the downstream Android kernel's, so the overlay corrupts nodes and the boot hangs with no output. Zeroing the active slot's `dtbo` partition stops ABL from applying the overlay.

### Untethered Boot
The working `build/boot.img` is flashed to `boot_b`, the active slot, so the phone boots Linux from power-on without a PC (verified 2026-11-22: same kernel, modules, Wi-Fi, touch, audio, sensors and charger as a `fastboot boot` of the same image). The slot keeps its zeroed `dtbo_b`; slot a is left alone because it still carries the stock DTBO and switching slots would also switch the xbl/abl firmware. `vbmeta_b` is untouched: verification stays enabled, and the unlocked bootloader (orange state) accepts the unsigned AVB hash footer. New images are still tried with `scripts/fastboot_boot.sh` first and written with `scripts/flash_boot.sh flash` once they work.

Getting back into fastboot from a flashed system needs a reboot reason, which a `fastboot boot`ed system never did (the ABL re-enters fastboot on its own after a `fastboot boot`). The DTS now carries the PM8150 PON `mode-bootloader = <2>` / `mode-recovery = <1>` properties and an IMEM `reboot-mode@65c` node (`0x77665500` / `0x77665502`, the values the OnePlus ABL reads), so `systemctl reboot --reboot-argument=bootloader` lands in fastboot. Two things had to go with it. systemd 262 silently ignores the positional `reboot bootloader` form, so the argument has to be `--reboot-argument=`. And the reason only survives a warm reset: `rmtfs -r` stops the modem remoteproc at shutdown, and with `wlan0` still up the WLAN firmware inside the modem keeps the MSA region assigned, the modem stop does not complete and the following reset is a hard reset that clears the reason (with Wi-Fi on, 4 of 5 attempts booted normally; with Wi-Fi off, 3 of 3 reached fastboot). `guacamole-wlan-down.service` (device package r12) is ordered after `rmtfs` and before NetworkManager, so at shutdown it takes `wlan0` down before `rmtfs` stops the modem; with it, 3 of 3 reboots with Wi-Fi connected reached fastboot. This is the same shutdown fault that used to end in crashdump mode before the download-mode cookie fix; the kernel side (ath10k holding the MSA region across a modem stop) is still open. The stock boot image is kept in `stock_boot_full.img` (gitignored) and restores with `fastboot flash boot_b stock_boot_full.img`.

### Cameras
The three rear cameras work through mainline CAMSS and libcamera since 2026-11-23: the Sony IMX586 main (4000x3000 RAW10 at 30 fps over a three-trio C-PHY link on CSIPHY1), the Samsung S5K3M5 telephoto (4208x3120 at 30 fps, CSIPHY0) and the Sony IMX481 ultra-wide (4656x3496 at 30 fps, CSIPHY3). Both rear LC898217XC lens actuators answer on CCI. The hardware is the same as the OnePlus 7T Pro's (the stock `vendor` partition names exactly these modules), so the kernel side is a port of the `hotdog-linux-bringup` camera series: SM8150 CAMSS backend with C-PHY support, the two CCI blocks, the sensor and lens drivers (kernel patches `0025`–`0045`). The flattened DTS adds the CCI buses, the `camss` node with its 31 clocks, interconnect votes and SMMU streams, PM8009 LDO1/3/4 for the sensor cores, the GPIO-switched analogue and autofocus rails, the pin states and the four camera slots. The pop-up front camera (IMX471, slot 2) does not answer on this unit (`failed to find sensor: -5`); its node and the matching `camss` endpoint are disabled, because `camss` only exposes its graph once every described sensor has bound. Capture with `cam -l` / `cam --camera <path> --capture=N --file=...` from `libcamera-tools`; cameras enumerate in a varying order, so address them by device-tree path. The PM8150L dual flash LED is enabled as well, which also gives Phosh a working torch.

Two problems were found on the way. The first session after a minute of idle failed with `CSID reset timeout` and left the graph dead until reboot (the OnePlus 7T Pro bringup records the same symptom as an open "CAMSS recovery" item). The trigger is the MMCX rail: once the display is idle it drops to low SVS (level 64), and the 600 MHz CSID clock does not come out of reset there. The `camss` node now carries `required-opps` (nominal for the two IFE domains), so the rail is raised while a pipeline is up; kernel patch `0046` makes camss park that vote whenever a VFE domain is off, since genpd otherwise keeps the attach-time vote of an unused domain forever and pins MMCX at nominal while idle. The second was memory corruption: libcamera's EGL debayer imports the V4L2 buffers into the GPU, and `msm_gem_free_object()` in 6.17.0 drops a bogus reference when such an imported dma-buf is freed (`WARN_ON` at `msm_gem.c:1127`, then `refcount_warn_saturate`). Two reboots hung on an oops in a daemon's exit path after camera sessions. Kernel patch `0047` is the upstream fix (`c34e08ba`, in `linux-6.17.y`).

User space: `device/testing/libcamera` is the pmaports libcamera package plus the OnePlus sensor data and software-ISP tuning files from the 7T Pro bringup (gain model, black level, control delays for S5K3M5, IMX586 and IMX481; libcamera 0.8.0 already knows the IMX471). The Phosh camera app reaches the cameras through PipeWire, whose libcamera plugin needs the repository's libcamera 0.8 line, so the package tracks pmaports' `temp/libcamera` 0.8.0. WirePlumber's libcamera monitor can stay enabled; `cam` opens the cameras alongside it. The Phosh camera app (Snapshot) reaches the cameras through the camera portal and PipeWire: with libcamera 0.8 and `pipewire-spa-libcamera` 1.6.11 installed, WirePlumber lists the three sensors as "Built-in Back Camera" sources and Snapshot streams from the IMX586 at 30 fps (2026-11-23). Autofocus runs in libcamera's software ISP (libcamera package r4, patch `0006`, a port of the 7T Pro's contrast autofocus onto 0.8.0): the CPU statistics add an exposure-normalised green edge energy, the IPA drives the lens through the simple pipeline, and a coarse-to-fine scan over the actuator range locks on the sharpest position (12x sharpness peak on a lit keyboard, lock within about 200 frames); it is enabled through the `Af` entry in the IMX586 and S5K3M5 tuning files and needs light to work, like any contrast method. Still open: the pop-up motor and Hall sensors for the front camera (hotdog patches `0103`–`0124`, only worth it if the sensor is alive), AF metering windows, auto-exposure and colour tuning, flash synchronisation, and demoting the per-frame VFE interrupt log line (kernel patch `0027`) now that the pipe is known good.

### Native Samsung Command-Mode DSC Display Driver
The OnePlus 7 Pro uses a high-density 1440x3120 90Hz Samsung AMOLED panel requiring **Command Mode (DCS)** and **Display Stream Compression (DSC v1.1)** with **2 slices per packet** (two 720-pixel slices transmitted together). Because Command Mode panels only update their internal Graphic RAM when the host DPU fires DCS write triggers, SimpleFB remains frozen. The `panel-samsung-oneplus-dsc` driver and a patch to the MSM DSI host timing calculations drive the panel at 90 Hz through the MSM DPU.

### Touchscreen Power Rail Routing
The `s6sy761` digitizer IC on the OnePlus 7 Pro is powered by **PM8150 LDO 17** (`vreg_l17a_3p0`, 3.0V), unlike the OnePlus 7T Pro which uses PM8150L. Additionally, GPIO 119 (`tp-1v8-active`) must be driven HIGH to enable the 1.8V digital rail. With both supplies configured, the controller probes at address `0x48` and reports multi-touch events on `/dev/input/event1`.

### Speaker Amplifiers
The loudspeakers are not driven by the WCD9340 codec. Two NXP TFA9874 amplifiers (I2C `0x34` top/earpiece, `0x35` bottom, on `i2c@890000`) receive audio over `QUATERNARY_MI2S_RX` at 48 kHz. Their register profile matches the stock `/vendor/firmware/tfa98xx.cnt`. Enforcing `S16LE` via WirePlumber aligns the audio samples with the DSP/TDM slots, restoring full acoustic volume across PipeWire. The WCD9340 on SLIMbus handles the microphones.

### Download-Mode Cookie and Reboot
Qualcomm boot firmware sets a download-mode cookie in TCSR at boot, so any reset that Linux does not mark as clean ends in Qualcomm crashdump mode (`05c6:900e`) instead of a reboot. The SCM driver clears the cookie at probe and on clean shutdown, but only when the device tree describes the register with `qcom,dload-mode`. Without it the driver falls back to an SCM call that does not clear the cookie on SM8150, and reboots with Wi-Fi on (the modem hosting the active WLAN firmware) dropped into crashdump mode. The device tree now adds the TCSR syscon at `0x1fc0000` and `qcom,dload-mode = <&tcsr 0x13000>` on the `scm` node, following the OnePlus 7T Pro bringup (`hotdog-linux-bringup` patch `0098`). Reboots with Wi-Fi connected now return to fastboot normally.

### Wi-Fi and Bluetooth Firmware Source
> [!NOTE]
> The WCN3990 Wi-Fi firmware (`wlanmdsp.mbn`, `WLAN.HL.3.0.c8`), its board data (`board-2.bin`) and the Bluetooth firmware (`crbtfw21.tlv`, `crnv21.bin`) are currently extracted from a LineageOS 24 OTA with `scripts/extract_lineage_firmware.py`. The extraction step creates a local, gitignored tarball that `firmware-oneplus-guacamole` builds from, so the package cannot yet be built from public URLs alone. The modem itself still uses the OxygenOS 11 build.

The public firmware in [sm8150-mainline/firmware-oneplus-sm8150](https://gitlab.com/sm8150-mainline/firmware-oneplus-sm8150) (`WLAN.HL.3.2.0`) does not work. Re-tested on 2026-10-12 with UFS writes verified, both with only its `wlanmdsp.mbn` and with its full modem, `wlanmdsp.mbn` and `board-2.bin` set: the firmware loads and scans, but every connection attempt fails with `vdev-start-response reports status error: -1` on 2.4 GHz and 5 GHz. The earlier failure was therefore not caused by storage corruption. That repository carries no Bluetooth firmware. The `linux-firmware` Bluetooth files (`qca/crbtfw21.tlv` `BTFM.CHE.2.1.3`, generic Qualcomm `qca/crnv21.bin`) also work (tested 2026-10-12: controller setup, scanning and a paired HID mouse). The package keeps the newer LineageOS files (`BTFM.CHE.2.1.5`, OnePlus NV data) because the Wi-Fi firmware needs the LineageOS extraction step anyway.

### Proprietary Firmware (Decompilation Targets)
All DSP and radio firmware is closed-source Qualcomm code. These blobs are long-term targets for decompilation and reverse engineering, with the aim of documenting their interfaces and eventually producing open-source replacements:

| Blob | Version | Runs on | Source |
| :--- | :--- | :--- | :--- |
| `wlanmdsp.mbn` | `WLAN.HL.3.0.c8` | Modem Hexagon DSP (WLAN process domain) | LineageOS 24 OTA |
| `board-2.bin` (`bdwlan.bin`) | — | WCN3990 calibration/board data | LineageOS 24 OTA |
| `crbtfw21.tlv`, `crnv21.bin` | `BTFM.CHE.2.1.5` | WCN3990 Bluetooth core | LineageOS 24 OTA |
| `modem.mdt` / `modem.bNN` | `MPSS.HE.1.0` (OxygenOS 11) | Modem Hexagon DSP | OxygenOS 11 |
| `ipa_fws.mbn` | — | IPA (modem data path) GSI firmware, loaded via TrustZone PAS | LineageOS 24 OTA (`vendor`) |
| `slpi.mdt` / `slpi.bNN` | `SLPI.HY.2.2-00083` (OxygenOS 11) | Sensor DSP (SSC/SEE, LSM6DSM, TCS3701, magnetometer, SAR drivers) | M1DNYT3 firmware repository |
| `sdsp/*.so`, `fastrpc_shell_2` | OxygenOS 11 | Hexagon libraries loaded into the sensor DSP over FastRPC | stock `dsp_b` partition |
| `adsp.mdt` / `adsp.bNN` | OxygenOS | Audio DSP | OxygenOS |
| `a640_zap.mdt` / `a640_zap.bNN` | OxygenOS | GPU secure-mode shader (TrustZone) | OxygenOS |
| `a640_gmu.bin` | `v2.0.261` | Adreno GPU management unit | `linux-firmware` |

The compute (CDSP) and sensor (SLPI) DSP firmware is not packaged yet; the SLPI image will join this list when sensor work starts.

The Hexagon DSP images are loaded through the TrustZone peripheral authentication service (PAS), which only accepts images signed by Qualcomm/OnePlus on a production device. An open-source rebuild of those images could not be loaded on retail hardware, so for them the realistic goal is documentation of the firmware interfaces (QMI, WMI, FastRPC) rather than a drop-in replacement.


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
│       ├── libcamera/              # pmaports libcamera plus the OnePlus 7 Pro sensor data and tuning files
│       └── linux-postmarketos-qcom-sm8150/
│           ├── APKBUILD            # SM8150 mainline kernel package recipe
│           ├── config-postmarketos-qcom-sm8150.aarch64 # Kernel Kconfig
│           └── *.patch             # Hardware patches (DSC panel, UFS, charger, IPA, CAMSS and camera sensors)
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
│   ├── flash_boot.sh               # 'test' = fastboot boot, 'flash' = write boot_b for untethered boot
│   └── ramoops.sh                  # Dumps pstore logs following kernel panic
│
└── docs/                           # Detailed technical documentation
    ├── PLAN.md                     # Bringup roadmap and status
    ├── PORTING.md                  # Kernel space vs user space split, for other distributions
    └── BRINGUP_GUIDE.md            # Hardware notes and bringup walkthrough
```

---

## Current Roadmap: Next Focus

- [ ] **Audio follow-ups** (see "Remaining audio work" in `docs/PLAN.md`):
  - Earpiece "receiver" profile and call audio routing.
  - Secondary microphones, speaker protection and default volume limits.
  - Settle on one sound server (PulseAudio vs PipeWire).
- [ ] **Wi-Fi, Bluetooth & Modem Bringup** (see "Wi-Fi, Bluetooth & Modem Bringup" in `docs/PLAN.md`):
  - Test WoWLAN.
  - With a SIM: validate registration, SMS, mobile data and calls via ModemManager (the modem is detected and the IPA data path is up).
- [ ] **Firmware decompilation** (long term): reverse-engineer the proprietary blobs listed under "Proprietary Firmware (Decompilation Targets)" towards open-source replacements, starting with the WCN3990 Wi-Fi and Bluetooth firmware.
- [ ] **Sensors** (see "Sensors" in `docs/PLAN.md`): gyroscope, magnetometer/compass, IMU temperature, and the proximity sensor for calls.
- [ ] **Camera** (see "Camera" in `docs/PLAN.md`): autofocus and exposure tuning in libcamera, the Phosh camera app over PipeWire, flash synchronisation; the pop-up front camera if its sensor turns out to be alive.
- [ ] **Battery & Charging** (see "Battery & Charging" in `docs/PLAN.md`):
  - Remove the diagnostic kernel patch `0023`; measure charge current and temperature on PD and DCP with a partly drained battery.
  - Warp Charge: reverse-engineer the OnePlus fast-charge MCU protocol (see "Battery & Charging" in `docs/PLAN.md`).