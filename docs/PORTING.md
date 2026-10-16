# Kernel space vs user space: what a port to another distribution needs

This splits the bringup into the parts that live in the kernel, the device tree
and firmware (reusable on any distribution that boots this kernel) and the parts
that live in postmarketOS user space (to be re-created for Mobian, Ubuntu Touch
or anything else). Status is as of 2026-10-16; `PLAN.md` carries the detail and
the evidence behind each item.

## Summary table

| Subsystem | Kernel / DT / firmware (portable) | postmarketOS user space (to port) | Porting notes |
| :--- | :--- | :--- | :--- |
| Boot | mkbootimg v2 image, AVB footer, cmdline (`scsi_mod.scan=sync`, ramoops); zeroed `dtbo` slot; DTB from `base_guacamole_working.dts` via `scripts/patch_dtb.py` | `deviceinfo` (pmOS only) | Any distro must build the same boot image; see `scripts/build_bootimg.sh` |
| Display, touch, GPU | patches `0004`, `0005`, `0006`; DT panel/touch nodes; `a640_zap` + `a640_gmu` firmware; Mesa freedreno | none | Needs a Mesa with freedreno/turnip, as every distro has |
| Storage | patch `0010` (UFS HS-G3 cap); 4096-byte sectors | none | Rootfs layout (pmOS image inside `userdata`) is pmOS-specific; another distro will choose its own |
| Audio (speakers, mic) | patches `0007`, `0008`; DT I2C/TFA9874/MI2S/SLIMbus nodes; `adsp` firmware; `CONFIG_SND_SOC_TFA9874` | ALSA UCM2 files `HiFi.conf`, `guacamole.conf` | UCM2 files are distro-neutral; install under `/usr/share/alsa/ucm2/`. PipeWire or PulseAudio both work with UCM |
| Modem DSP, Wi-Fi | patch `0009`; DT wifi/regulators, reserved memory, `qcom,dload-mode`; `modem` (OOS11), `wlanmdsp.mbn` (OOS12, LineageOS), `board-2.bin`, `firmware-5.bin` | `rmtfs`, `tqftpserv` (serve files to the modem); `guacamole-wlanmac` + udev rule (factory MAC); NetworkManager | `rmtfs`/`tqftpserv` exist in Debian (`rmtfs`, `qrtr-tools`/`tqftpserv`) and UT. The in-kernel pd-mapper (`CONFIG_QCOM_PD_MAPPER`) replaces the userspace one |
| Bluetooth | DT UART13 + `qcom,wcn3990-bt` node, `serial1` alias; `crbtfw21.tlv`, `crnv21.bin` | `guacamole-bdaddr` + udev rule + oneshot unit (public address from the factory MAC, via `btmgmt`) | Needs `btmgmt` (bluez). Without it the controller stays unconfigured and BlueZ ignores it |
| Cellular (data path) | patches `0013`–`0016` (IPA v4.1); DT `ipa@1e40000`, SMP2P entries, `usb-psy-name`; `ipa_fws.mbn` | ModemManager (qcom-soc plugin), `msm-modem-uim-selection` | Untested with a SIM. Debian/UT ship ModemManager with the same plugin |
| USB host/OTG | DT: PM8150B Type-C + VBUS regulator, `usb-c-connector`, role switch, QMP orientation switch | none | Works with any distro |
| Reboot | DT `qcom,dload-mode` (TCSR) | none | Without it, a reboot with Wi-Fi on lands in Qualcomm crashdump mode |
| Battery, charging | patches `0011`, `0012`, `0018`–`0024`; DT `battery` node (4.35 V, 3 A), charger node, sink PDO 5 V/3 A | `guacamole-chgctrl` (policy daemon), its unit, `/etc/conf.d/guacamole-chgctrl`, systemd preset | The daemon is plain Python 3 with no distro dependencies; it needs `/sys/class/power_supply` and systemd (or an init script, one is provided for OpenRC) |
| Sensors (auto-rotate, light) | patch `0017`; DT SLPI enabled, FastRPC pool; `slpi.mdt`/`.bNN`, `slpir.jsn`, `slpius.jsn` | `hexagonrpcd` (patched), the served tree in `/usr/share/qcom`, `guacamole-sensors-registry` (imports the per-unit registry from `persist`), udev rules (start order, mount matrix), `iio-sensor-proxy` (patched, libssc build) | The heaviest port: see the sensors section |
| Volume keys | DT `gpio-keys` on PM8150 GPIO 6/7 | none | — |

## Kernel space

### Kernel tree and patches

The kernel is the `v6.17.0-sm8150` tag of
`gitlab.com/sm8150-mainline/linux`, built with `LLVM=1`, with the patches in
`device/testing/linux-postmarketos-qcom-sm8150/`:

| Patch | Area | Why |
| :--- | :--- | :--- |
| `0001`–`0003` | build, UFS, lid switch | pmOS/sm8150-mainline housekeeping |
| `0004` | DRM MSM DSI, panel | Samsung DSC panel, 2 DSC slices per packet, 90 Hz |
| `0005` | input s6sy761 | optional reset GPIO for the touchscreen |
| `0006` | I2C geni | FIFO mode (no GPI DMA) |
| `0007` | ASoC codecs | TFA9874 speaker amplifier driver |
| `0008` | ASoC sm8150 | QUATERNARY_MI2S_RX backend, per-SLIMbus-link channel maps |
| `0009` | ath10k | skip the WMI quiet-mode command on WCN3990 |
| `0010` | UFS qcom | cap SM8150 at HS-G3 (HS-G4 drops writes) |
| `0011` | qcom_smbx | SMB5 limits and AICL (float voltage, fast-charge current, ICL bits) |
| `0012` | bq27xxx | report Full only while supplied |
| `0013`–`0016` | net/ipa | IPA v4.1 data, registers, bounded GSI wait, ENDP_INIT_CTRL |
| `0017` | misc fastrpc | sensors-PD message buffers from the reserved pool |
| `0018`, `0019` | qcom_smbx | USB3 SDP current; writable `input_current_limit` |
| `0020` | qcom_smbx | PM8150B input window override (`USBIN_ADAPTER_ALLOW_OVERRIDE`) |
| `0021` | qcom-pmic-typec | VBUS presence from the SM status (inert, kept) |
| `0022` | qcom_smbx | follow the TCPM contract: Rp/standby/contract current, voltage window, 500 mA floor |
| `0023` | qcom-pmic-typec | diagnostic: port status on VBUS interrupts (to be dropped) |
| `0024` | qcom-pmic-typec | exit the sink state on CC only (fixes the PD voltage-step detach) |

Every patch is against mainline drivers, not pmOS-specific code, so they apply
to any 6.17-based tree. Several come from the OnePlus 7T Pro bringup
(`hotdog-linux-bringup`), as noted in their headers.

### Kernel configuration

Beyond pmOS's `config-postmarketos-qcom-sm8150.aarch64`, the options this
device relies on (a distro kernel config should include them):

- `CONFIG_SND_SOC_TFA9874=m` (added by this project), the QDSP6 ASoC stack, `CONFIG_SLIMBUS`, `CONFIG_SND_SOC_WCD934X`.
- `CONFIG_QCOM_IPA=m`, `CONFIG_RMNET=m` (cellular data path).
- `CONFIG_QCOM_FASTRPC=m`, `CONFIG_QCOM_PD_MAPPER=m` (in-kernel pd-mapper; no userspace `pd-mapper` needed), `CONFIG_QRTR*`, `CONFIG_QCOM_Q6V5_PAS=m`.
- `CONFIG_TYPEC_QCOM_PMIC=y`, `CONFIG_TYPEC_TCPM=y`, `CONFIG_USB_ROLE_SWITCH=y`, `CONFIG_USB_DWC3_DUAL_ROLE=y`, `CONFIG_REGULATOR_QCOM_USB_VBUS=y` (USB host and PD).
- `CONFIG_CHARGER_QCOM_SMB2=y` (the `qcom_smbx` driver), `CONFIG_BATTERY_BQ27XXX_I2C` with `CONFIG_BATTERY_BQ27XXX_DT_UPDATES_NVM` **off**.
- `CONFIG_QCOM_SCM=y` with the `qcom,dload-mode` DT property (clean reboots).
- `CONFIG_PSTORE_RAM` for ramoops (debugging only).

### Device tree

The device tree is maintained as a flattened DTS (`base_guacamole_working.dts`)
plus `scripts/patch_dtb.py`. Relative to the upstream
`sm8150-oneplus-guacamole.dts` it adds or changes:

- Reserved memory matching the stock map (splash/rdump, ramoops, bootloader log, cdsp_sec, param, mtp, `ipa_fw` at `0x98b00000`), plus a 16 MiB FastRPC pool below 4 GiB assigned to HLOS/SSC/ADSP.
- `qcom,msm-id` / `qcom,board-id` so ABL accepts the DTB.
- Audio: QUP0 wrapper and `i2c@890000` (TFA9874 at 0x34/0x35), QUAT MI2S pinctrl, `q6afedai` dai@22, sound card routing.
- Fuel gauge `ti,bq27411` on `i2c@a80000` (no `monitored-battery`); `battery` node (4.35 V float, 3 A fast charge); `charger@1000` enabled.
- Wi-Fi regulators and supplies; `qcom,dload-mode` on `scm` with a TCSR syscon.
- Volume keys (`gpio-keys`, PM8150 GPIO 6/7).
- Bluetooth: `serial1` alias, `serial@c8c000` with a `qcom,wcn3990-bt` child.
- USB: `dr_mode = "otg"`, `usb-role-switch`, `usb-psy-name = "pm8150b-charger"`, PM8150B Type-C (`usb-c-connector`, sink PDO 5 V/3 A only) and VBUS regulator, QMP combo PHY orientation switch.
- IPA: `ipa@1e40000`, SMP2P `ipa-ap-to-modem`/`ipa-modem-to-ap`, `system-noc` phandle.
- SLPI remoteproc enabled with `firmware-name`, SDSP FastRPC `memory-region` and `qcom,vmids`.

A port should carry these as a proper DTS on top of upstream; `PLAN.md` has
the exact property values and the reasons for each.

### Firmware

All files are loaded by the kernel (or served to a DSP by `tqftpserv`/`hexagonrpcd`)
from `/lib/firmware`. Sources:

| Files | Source | Installed by |
| :--- | :--- | :--- |
| `qcom/sm8150/oneplus7/modem.*`, `adsp.*`, `slpi.*`, `qcom/a640_zap.*` | M1DNYT3 firmware repository (OxygenOS 11) | `firmware-oneplus-guacamole` |
| `postmarketos/qcom/sm8150/oneplus7/wlanmdsp.mbn` (WLAN.HL.3.0.c8), `ath10k/WCN3990/hw1.0/board-2.bin`, `qca/crbtfw21.tlv`, `qca/crnv21.bin`, `qcom/sm8150/oneplus7/ipa_fws.mbn`, `slpir.jsn`, `slpius.jsn` | LineageOS 24 OTA, via `scripts/extract_lineage_firmware.py` | same |
| `ath10k/WCN3990/hw1.0/firmware-5.bin`, `qcom/a640_gmu.bin`, `qcom/a630_sqe.fw` | linux-firmware | same / `firmware-qcom-adreno-a640` |

The `postmarketos/` prefix for `wlanmdsp.mbn` is only a `tqftpserv` search
path convention; another distro puts it wherever its `tqftpserv` looks.

## User space (postmarketOS specific, to re-create)

Everything below is in `device/testing/device-oneplus-guacamole/` unless noted.
None of it is large; most of it is glue around generic daemons.

### Generic daemons the device needs

| Daemon | Role | Debian / Ubuntu Touch |
| :--- | :--- | :--- |
| `rmtfs` | modem EFS storage over QRTR; the modem does not start without it | `rmtfs` |
| `tqftpserv` | serves `wlanmdsp.mbn` and `modemuw.jsn` to the modem | `qrtr-tools` / `tqftpserv` |
| ModemManager with the `qcom-soc` plugin | cellular (QMI over QRTR, `rmnet_ipa0`) | standard |
| NetworkManager | Wi-Fi; per-connection stable MAC policy | standard |
| BlueZ + `btmgmt` | Bluetooth; `btmgmt public-addr` sets the controller address | `bluez` |
| UPower | battery to the UI; its Critical action powers the phone off on the gauge's Critical level | standard |
| `hexagonrpcd` 0.4.0 **with the writable-file-service patches** (`device/testing/hexagonrpcd/`) | FastRPC file server for the SLPI sensor process | not in Debian; build from `github.com/linux-msm/hexagonrpc` plus the four patches |
| `iio-sensor-proxy` 3.9 **built with libssc** and the D-Bus-ordering patch (`device/testing/iio-sensor-proxy/`) | SSC sensors (accelerometer, light, proximity) to `net.hadess.SensorProxy` | Debian's build has no libssc; needs `libssc` and a rebuild with `-Dssc-support=enabled` plus the patch |
| `libssc`, `libqrtr-glib`, `libqmi` | QMI over QRTR for sensors and the modem | `libqmi` is packaged; `libssc` may need packaging |
| ALSA UCM2 | speaker and mic routing | `alsa-ucm-conf` plus the two device files |
| Docker (optional) | only for the demo web server | — |

### Device-specific pieces

| Piece | Kind | What it does | Portability |
| :--- | :--- | :--- | :--- |
| `HiFi.conf`, `guacamole.conf` | ALSA UCM2 | speakers on QUAT_MI2S_RX, mic on SLIMbus TX0 | copy as is to `/usr/share/alsa/ucm2/` |
| `guacamole-wlanmac`, `90-guacamole-wlanmac.rules` | shell + udev `RUN+=` | reads `Intf0MacAddress` from `persist/wlan_mac.bin` with `debugfs` (udevd blocks `mount`) and sets it on `wlan0` before NetworkManager manages it | portable; needs `e2fsprogs` (`debugfs`) |
| `guacamole-bdaddr`, `guacamole-bdaddr.service`, `90-guacamole-bdaddr.rules` | shell + oneshot + udev `SYSTEMD_WANTS` | derives the BT address from the Wi-Fi MAC, waits for the controller to report "missing public-address", runs `btmgmt public-addr` | portable; UT/upstart needs an equivalent trigger on `hci0` |
| `guacamole-chgctrl` (Python), `.service`, `.confd`, `80-guacamole.preset` | daemon | charge policy: input limit from the PD contract / BC1.2 type / PC port, thermal throttle, charge window, source indicator in `/run/guacamole/charger` | portable (Python 3 stdlib only); `guacamole-chgctrl.initd` for OpenRC |
| `guacamole-sensors-registry`, `.service` | shell + oneshot | first boot: copies the SLPI sensor registry from `persist` (via `debugfs`) to `/var/lib/guacamole/sensors`, writes `project_info/project_name` from `androidboot.project_name` | portable |
| `/usr/share/qcom/...` tree (from `guacamole-sensors-<date>.tar.gz`, built by `scripts/extract_sensor_files.sh`) | data | `sensors/config` (61 JSONs from `vendor_b`), `sensors/sns_reg.conf`, `sdsp/` (SLPI libraries from `dsp_b`), `socinfo/`, symlinks to the writable registry | portable data; the registry snapshot is one unit's factory calibration and only a fallback |
| `90-guacamole-sensors.rules` | udev `SYSTEMD_WANTS` | starts the registry import, `hexagonrpcd-sdsp` and `iio-sensor-proxy` when `/dev/fastrpc-sdsp` appears | systemd-specific; port the ordering: registry → hexagonrpcd → (8 s) → iio-sensor-proxy, before the compositor claims sensors |
| `iio-sensor-proxy-guacamole.conf` | systemd drop-in | `After=hexagonrpcd-sdsp.service`, `ConditionPathExists=/dev/fastrpc-sdsp`, 8 s delay | systemd-specific |
| `61-guacamole-accel-mount-matrix.rules` | udev | `ACCEL_MOUNT_MATRIX="-1, 0, 0; 0, -1, 0; 0, 0, 1"` on the FastRPC nodes (IMU rotated 180°) | portable udev |
| `90-wifi-wowlan.conf`, `90-ath10k-wowlan.rules`, `10-wifi-wowlan` | NM conf, udev, dispatcher | WoWLAN (untested) | NetworkManager-specific |
| `guacamole-mpss.initd` | OpenRC | starts the modem remoteproc after `rmtfs` (systemd boots it automatically through the in-kernel pd-mapper and `rmtfs.service`) | OpenRC only |
| `sxmo_deviceprofile-oneplus-guacamole.sh` | Sxmo | button profile | pmOS/Sxmo only |
| `deviceinfo` | pmOS | boot image parameters | pmOS only (translate to the distro's boot tooling) |

### Configuration done by hand on the test phone (not packaged)

- `/etc/systemd/system/usb-internet.service`: USB tethering route via `172.16.42.2` at metric 30000 (must stay above NetworkManager's 20000 connectivity penalty).
- `/etc/conf.d/guacamole-chgctrl`: `CHG_SDP_UA=900000` for the USB 3 PC port.
- `org.gnome.settings-daemon.plugins.power ambient-enabled true` (Phosh automatic brightness).
- The demo web server (`~/Documents/web_server`, Docker Compose) and the NetworkManager connection profiles.

### Compositor and UI expectations

- Auto-rotate and automatic brightness need a compositor that consumes `net.hadess.SensorProxy` (Phosh does; Lomiri on Ubuntu Touch uses its own sensor framework and would need an adapter or libssc support).
- Phosh releases the accelerometer while the screen is off; the proxy must be running and enumerated before the compositor claims sensors at boot (hence the ordering above and the iio-sensor-proxy patch).
- Battery percentage shown by the UI is the gauge's `capacity` register (voltage-aware); the shutdown trigger is its Critical level.

## Moving to a newer kernel

Checked 2026-10-16 against the trees that matter:

- The device support tree moved: postmarketOS now builds `linux-postmarketos-qcom-sm8150` **7.0.0** from `gitlab.postmarketos.org/soc/qualcomm-sm8150/linux`, tag `v7.0.0-sm8150` (2026-06-26), with three small patches of its own (`enable-ufs`, a libbpf fix, a vayu OTG fix). The old `gitlab.com/sm8150-mainline/linux` stops at `v6.17.0-sm8150`. There is no 7.1/7.2 tag of either; mainline is at 7.3-rc.
- That tree carries about 80 commits over upstream (SMB5 charger driver, the OnePlus/Xiaomi device trees, panels, touch drivers, a few `FROMLIST` patches). Rebasing it to 7.2.9 by hand is the pmOS maintainers' job every few releases; doing it here means carrying those 80 as well as ours.

So the practical step is `v6.17.0-sm8150` → `v7.0.0-sm8150`, not → 7.2.9. What that costs, from a dry run of our 24 patches against the files at `v7.0.0-sm8150`:

| Patch | At v7.0.0-sm8150 | Action |
| :--- | :--- | :--- |
| `0001` lid switch, `0003` LLVM build | already in the tree | drop |
| `0002` enable UFS | applies; pmaports 7.0.0 ships its own copy | use theirs |
| `0004` DSC panel + DSI, `0005` touch reset, `0007` TFA9874, `0009` ath10k, `0010` UFS HS-G3, `0011` SMB5 limits, `0012` bq27xxx, `0017` FastRPC, `0019` ICL property, `0020` input window, `0021`, `0023`, `0024` Type-C | apply (some with offset) | keep |
| `0013`, `0014`, `0016` IPA v4.1 | already in the tree (`ipa_data-v4.1.c`, `qcom,sm8150-ipa`) | drop |
| `0015` bounded `gsi_trans_commit_wait()` | still needed (`wait_for_completion` unbounded) | keep |
| `0006` geni I2C FIFO mode | 2 of 3 hunks fail; the driver's DMA/FIFO selection was reworked | rebase, or test whether it is still needed |
| `0008` QUAT MI2S + SLIMbus maps | 2 of 4 hunks fail; `sm8150.c` already handles `QUATERNARY_MI2S_RX` in `hw_params` | rebase the remaining half |
| `0018` USB3 SDP current, `0022` TCPM follow | hunks fail (context moved in `qcom_smbx.c`) | rebase (mechanical) |

Beyond the patches:

- **Device tree:** this is the real work. `base_guacamole_working.dts` is a flattened copy of the 6.17 DTB; the 7.0 tree's `sm8150-oneplus-guacamole.dts` is 69 lines (panel, touch) plus a 544-line common dtsi (modem, Wi-Fi, remoteprocs, UFS), and `sm8150.dtsi` now carries the IPA node. None of our additions (TFA9874/I2C/audio routing, bq27411, charger and battery, Type-C connector and VBUS, Bluetooth UART, `qcom,dload-mode`, volume keys, SLPI enable and FastRPC pool, SMP2P IPA entries, reserved-memory fix-ups) are there. Rebuild the DTB from 7.0, re-flatten, and re-apply the deltas listed under "Device tree" above; better, turn them into a proper `.dts` on top of the tree so the next move is a rebase instead of a re-derivation. `scripts/patch_dtb.py` anchors on exact text and will need its anchors checked.
- **Config:** start from pmaports' 7.0.0 `config-postmarketos-qcom-sm8150.aarch64` and re-add this project's options (`CONFIG_SND_SOC_TFA9874=m` and the list under "Kernel configuration").
- **User space and firmware:** unchanged. Everything talks to stable interfaces (`/sys/class/power_supply`, `/dev/fastrpc-*`, QRTR, ALSA UCM, `net.hadess.SensorProxy`). The only coupling is the writable `input_current_limit` property, which `0019` provides.
- **Verification:** the same hardware checklist as `PLAN.md`: charger registers `0x1070`/`0x1061`/`0x1370` before leaving the phone on a charger, UFS write integrity, Wi-Fi/BT/modem detection, sensors, PD 5 V contract.

Rough size: a day for patches and config, two to three days for the device tree and re-verification, assuming the 7.0 tree boots guacamole as it claims (panel and touch) and nothing regressed in the SMB5 or sensor paths.

## Not done anywhere yet

Earpiece and call audio, cellular with a SIM, the gyroscope/compass in user space, proximity for calls, cameras, Warp Charge (needs the OnePlus fast-charge MCU protocol), DisplayPort alternate mode, the FSA4480 audio switch, and the fingerprint sensor (TrustZone-bound). See `PLAN.md`.
