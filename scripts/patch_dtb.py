import os
import subprocess

with open("/tmp/base_guacamole.dts", "r") as f:
    content = f.read()

root_marker = 'model = "OnePlus 7 Pro";'
qcom_props = '''model = "OnePlus 7 Pro";
\tqcom,msm-name = "SM8150 V2";
\tqcom,msm-id = <0x153 0x20000>;
\tqcom,pmic-name = "PM8150";
\tqcom,board-id = <0x08 0x00 0x00 0x00>;'''

if root_marker in content:
    content = content.replace(root_marker, qcom_props, 1)
else:
    print("Warning: root marker not found")

res_mem_marker = "memory@a1a10000 {"
ramoops_node = '''ramoops: ramoops@a9800000 {
\t\t\tcompatible = "ramoops";
\t\t\treg = <0x00 0xa9800000 0x00 0x400000>;
\t\t\trecord-size = <0x40000>;
\t\t\tconsole-size = <0x40000>;
\t\t\tftrace-size = <0x40000>;
\t\t\tpmsg-size = <0x200000>;
\t\t};

\t\tmemory@a1a10000 {'''

if res_mem_marker in content:
    content = content.replace(res_mem_marker, ramoops_node, 1)
else:
    print("Warning: res_mem_marker not found")

with open("/tmp/custom_guacamole.dts", "w") as f:
    f.write(content)

print("Modified DTS written to /tmp/custom_guacamole.dts")
subprocess.run(["dtc", "-I", "dts", "-O", "dtb", "/tmp/custom_guacamole.dts", "-o", "/tmp/custom_guacamole.dtb"], check=True)
print(f"DTB compiled successfully! Size: {os.path.getsize('/tmp/custom_guacamole.dtb')} bytes")
