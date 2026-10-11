#!/usr/bin/env python3
import os
import subprocess

def patch():
    with open("/tmp/base_guacamole_r4.dts") as f:
        text = f.read()

    # 1. Fix memory@85d00000 -> 0x85e00000 (xbl_aop_mem)
    text = text.replace("memory@85d00000 {\n\t\t\treg = <0x00 0x85d00000 0x00 0x140000>;",
                        "memory@85e00000 {\n\t\t\treg = <0x00 0x85e00000 0x00 0x140000>;")

    # 2. Fix memory@86200000 size: 0x3900000 -> 0x5500000 (removed_regions: prevents TrustZone XPU reset!)
    text = text.replace("memory@86200000 {\n\t\t\treg = <0x00 0x86200000 0x00 0x3900000>;",
                        "memory@86200000 {\n\t\t\treg = <0x00 0x86200000 0x00 0x5500000>;")

    # 5. Add missing hardware security regions (bootloader_log, cdsp_sec, ramoops, param, mtp)
    target_end_rm = """\t\tmemory@f2901000 {
\t\t\tcompatible = "qcom,rmtfs-mem";
\t\t\treg = <0x00 0xf2901000 0x00 0x200000>;
\t\t\tno-map;
\t\t\tqcom,client-id = <0x01>;
\t\t\tqcom,vmid = <0x0f>;
\t\t};
\t};"""

    missing_regions = """\t\tmemory@f2901000 {
\t\t\tcompatible = "qcom,rmtfs-mem";
\t\t\treg = <0x00 0xf2901000 0x00 0x200000>;
\t\t\tno-map;
\t\t\tqcom,client-id = <0x01>;
\t\t\tqcom,vmid = <0x0f>;
\t\t};

\t\tbootloader_log_mem@9fff7000 {
\t\t\treg = <0x00 0x9fff7000 0x00 0x9000>;
\t\t\tno-map;
\t\t};

\t\tcdsp_sec_regions@a4c00000 {
\t\t\tcompatible = "removed-dma-pool";
\t\t\tno-map;
\t\t\treg = <0x00 0xa4c00000 0x00 0x3c00000>;
\t\t};

\t\tramoops: ramoops@a9800000 {
\t\t\tcompatible = "ramoops";
\t\t\treg = <0x00 0xa9800000 0x00 0x400000>;
\t\t\trecord-size = <0x40000>;
\t\t\tconsole-size = <0x40000>;
\t\t\tftrace-size = <0x40000>;
\t\t\tpmsg-size = <0x200000>;
\t\t};

\t\tparam_mem@ac200000 {
\t\t\treg = <0x00 0xac200000 0x00 0x100000>;
\t\t\tno-map;
\t\t};

\t\tmtp_mem@ac300000 {
\t\t\treg = <0x00 0xac300000 0x00 0xb00000>;
\t\t\tno-map;
\t\t};
\t};"""
    assert target_end_rm in text, "Target end of reserved memory not found"
    text = text.replace(target_end_rm, missing_regions, 1)

    # 6. Add Qualcomm bootloader matching IDs
    root_marker = "model = \"OnePlus 7 Pro\";"
    qcom_props = """model = "OnePlus 7 Pro";
\tqcom,msm-name = "SM8150 V2";
\tqcom,msm-id = <0x153 0x20000>;
\tqcom,pmic-name = "PM8150";
\tqcom,board-id = <0x08 0x00 0x00 0x00>;"""
    text = text.replace(root_marker, qcom_props, 1)

    out_dts = "/tmp/patched_guacamole.dts"
    out_dtb = "/tmp/custom_guacamole.dtb"
    with open(out_dts, "w") as out:
        out.write(text)

    subprocess.run(["dtc", "-I", "dts", "-O", "dtb", out_dts, "-o", out_dtb], check=True)
    print(f"Patched DTB compiled successfully: {out_dtb} ({os.path.getsize(out_dtb)} bytes)")

if __name__ == "__main__":
    patch()
