# Firmware Management for OnePlus 7 Pro (guacamole)

## Overview
Qualcomm SM8150 devices rely on proprietary firmware binaries to run peripheral subsystems:
- **Modem / Baseband (`remoteproc0`, `modem.b*` / `q6v5_pas`)**: Cellular telephony, LTE/5G.
- **ADSP (`audio-dsp`)**: Audio processing, DSP, low-power audio decoding.
- **CDSP (`compute-dsp`)**: Neural Processing Engine, computer vision acceleration.
- **SLPI (`sensors-dsp`)**: Sensor processing subsystem (accelerometer, gyro, ALS).
- **Wi-Fi (`ath10k_snoc` / WCN3990)**: WLAN (`wlanmdsp.mbn`, firmware-5.bin, board-2.bin).
- **Bluetooth (`hci_qca` / WCN3990)**: Bluetooth firmware (`nvm`, `rampatch`).
- **GPU (`freedreno` / `qcom,adreno-640`)**: GPU microcode (`a640_zap.mbn`, `a640_gmu.bin`).

## Firmware Partition Sources
On the OnePlus 7 Pro, firmware blobs reside in the following partitions:
- `/dev/block/bootdevice/by-name/modem_[a|b]` (FAT32 filesystem containing modem and DSP images)
- `/dev/block/bootdevice/by-name/vendor_[a|b]` (`/vendor/firmware/`)
- `/dev/block/bootdevice/by-name/persist` (Device-unique calibration and sensor data, Wi-Fi MAC)

## Extracting Firmware from Stock OxygenOS OTA
1. Download a stock OxygenOS zip or recovery ROM for the OnePlus 7 Pro.
2. Extract `payload.bin` using `payload-dumper-go`:
   ```bash
   payload-dumper-go -p modem,vendor payload.bin
   ```
3. Mount the extracted `modem.img`:
   ```bash
   mkdir -p /tmp/modem
   sudo mount -o loop,ro modem.img /tmp/modem
   ```
4. Copy necessary binaries:
   - DSP: `/tmp/modem/image/adsp*`, `/tmp/modem/image/cdsp*`, `/tmp/modem/image/slpi*`
   - Modem: `/tmp/modem/image/modem*`, `/tmp/modem/image/mba*`
   - Wi-Fi: `/tmp/modem/image/wlanmdsp.mbn`

## Known Issues (from Nura Wiki)
- **ath10k / WCN3990 Crash**:
  Firmware ver `1.0.0.698 api 5` extracted from stock OTAs has reported WMI vdev / HIF initialization crashes (`-108`, `-110`).
  Investigation into board data (`board-2.bin` calibration) and firmware API revisions is ongoing in the SM8150 community.
