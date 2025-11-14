#!/usr/bin/env bash
# unified_install.sh — choose best flow automatically (Unix)
set -euo pipefail

OS="$(uname -s)"
case "$OS" in
  Linux) echo "Detected Linux";;
  Darwin) echo "Detected macOS";;
  *) echo "Unrecognized OS ($OS). Attempting Linux flow.";;
esac

# call install.sh (this does validation and everything)
if [ -f "./install.sh" ]; then
  chmod +x ./install.sh
  exec ./install.sh
else
  echo "install.sh missing. Please ensure install.sh is present."
  exit 1
fi
