#!/bin/bash
# Build the PyInstaller onefile binary
# Usage: ./build_scripts/build_binary.sh
# Assumes: dependencies already installed in your environment

set -e
cd "$(dirname "$0")/.."

echo "=== Comic Strip Browser — Binary Build ==="

rm -rf build/onefile dist/onefile

python3 -m PyInstaller comic_browser.spec \
    --clean --noconfirm \
    --distpath dist/onefile \
    --workpath build/onefile

BINARY="dist/onefile/comic-strip-browser"
[ -f "$BINARY" ] && echo "✓ $BINARY ($(du -h "$BINARY" | cut -f1))" || { echo "✗ Failed"; exit 1; }
