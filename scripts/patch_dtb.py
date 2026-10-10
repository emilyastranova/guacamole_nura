#!/usr/bin/env python3
import os
import subprocess

def patch():
    with open("/tmp/base_guacamole.dts") as f:
        text = f.read()

    # 1. Fix memory@85d00000 -> 0x85e00000 (xbl_aop_mem)
    text = text.replace("memory@85d00000 {\n\t\t\treg = <0x00 0x85d00000 0x00 0x140000>;",
                        "memory@85e00000 {\n\t\t\treg = <0x00 0x85e00000 0x00 0x140000>;")

    # 2. Fix memory@86200000 size: 0x3900000 -> 0x5500000 (removed_regions: prevents TrustZone XPU reset!)
    text = text.replace("memory@86200000 {\n\t\t\treg = <0x00 0x86200000 0x00 0x3900000>;",
                        "memory@86200000 {\n\t\t\treg = <0x00 0x86200000 0x00 0x5500000>;")

    # 3. Fix splash size in memory@a1a10000 to 0x2400000 (36 MB)
    text = text.replace("memory@a1a10000 {\n\t\t\tcompatible = \"removed-dma-pool\";\n\t\t\tno-map;\n\t\t\treg = <0x00 0x9c000000 0x00 0x1123800>;",
                        "memory@a1a10000 {\n\t\t\tcompatible = \"removed-dma-pool\";\n\t\t\tno-map;\n\t\t\treg = <0x00 0x9c000000 0x00 0x2400000>;")

    # 4. Fix chosen framebuffer reg to match continuous splash
    text = text.replace("framebuffer@9C000000 {\n\t\t\tcompatible = \"simple-framebuffer\";\n\t\t\treg = <0x00 0x9c000000 0x00 0x1123800>;",
                        "framebuffer@9C000000 {\n\t\t\tcompatible = \"simple-framebuffer\";\n\t\t\treg = <0x00 0x9c000000 0x00 0x2400000>;")

    # 5. Add missing hardware security regions (cdsp_sec_regions, param_mem, mtp_mem, bootloader_log, ramoops)
    missing_regions = """
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
\t};
"""

    target = """\t\tmemory@a1a10000 {
\t\t\tcompatible = "removed-dma-pool";
\t\t\tno-map;
\t\t\treg = <0x00 0x9c000000 0x00 0x2400000>;
\t\t};
\t};"""

    assert target in text, "Target end of reserved-memory not found"
    text = text.replace(target, """\t\tmemory@a1a10000 {
\t\t\tcompatible = "removed-dma-pool";
\t\t\tno-map;
\t\t\treg = <0x00 0x9c000000 0x00 0x2400000>;
\t\t};
""" + missing_regions, 1)

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
