#!/usr/bin/env bash
set -e

# Helper script for building the kernel with envkernel.sh
# Usage: ./scripts/build_kernel.sh [path/to/linux-source]

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KERNEL_SRC="${1:-}"

if [ -z "$KERNEL_SRC" ]; then
    echo "Usage: $0 /path/to/sm8150/linux"
    echo "Or set KERNEL_SRC environment variable."
    exit 1
fi

if [ ! -d "$KERNEL_SRC" ]; then
    echo "Error: Directory '$KERNEL_SRC' does not exist."
    exit 1
fi

echo "=== Building Kernel with envkernel.sh ==="
cd "$KERNEL_SRC"

# Source pmbootstrap envkernel
source "$REPO_ROOT/pmbootstrap/helpers/envkernel.sh"

echo "[1/3] Ensuring SM8150 configuration..."
if [ ! -f .config ]; then
    if [ -f "$REPO_ROOT/device/testing/linux-postmarketos-qcom-sm8150/config-postmarketos-qcom-sm8150.aarch64" ]; then
        cp "$REPO_ROOT/device/testing/linux-postmarketos-qcom-sm8150/config-postmarketos-qcom-sm8150.aarch64" .config
        make olddefconfig
    else
        make defconfig sm8150.config
    fi
fi

echo "[2/3] Compiling kernel and DTBs..."
make -j"$(nproc)"

echo "[3/3] Building Nura / pmOS package..."
pmbootstrap build --envkernel linux-postmarketos-qcom-sm8150

echo "=== Kernel build complete ==="
