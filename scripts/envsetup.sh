#!/usr/bin/env bash
# Source this file to initialize your development environment:
#   source scripts/envsetup.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ensure ~/.local/bin is on PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Ensure pmbootstrap helper directory is accessible
export PMB_DIR="$REPO_ROOT/pmbootstrap"
export PMB_HELPERS="$PMB_DIR/helpers"

alias pmb="pmbootstrap"
alias pmb-guacamole="pmbootstrap --device=oneplus-guacamole"

# Helper function to source envkernel in a kernel source tree
envkernel() {
    if [ -f "$PMB_HELPERS/envkernel.sh" ]; then
        source "$PMB_HELPERS/envkernel.sh"
    else
        echo "Error: $PMB_HELPERS/envkernel.sh not found!"
        return 1
    fi
}

echo "=== Guacamole Nura Environment Initialized ==="
echo "Repo root:    $REPO_ROOT"
echo "pmbootstrap:  $(which pmbootstrap 2>/dev/null || echo 'not found in PATH')"
echo "Helpers:      $PMB_HELPERS"
echo "Aliases:      pmb, pmb-guacamole, envkernel"
