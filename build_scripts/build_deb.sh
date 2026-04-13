#!/bin/bash
# Build .deb package (Debian/Ubuntu only)
# Usage: ./build_scripts/build_deb.sh
# Requires: build_binary.sh run first

set -e
cd "$(dirname "$0")/.."

echo "=== Comic Strip Browser — .deb Build ==="

command -v dpkg-deb &>/dev/null || { echo "✗ dpkg-deb not found — install dpkg-dev"; exit 1; }

BINARY="dist/onefile/comic-strip-browser"
[ -f "$BINARY" ] || { echo "✗ Binary not found — run build_binary.sh first"; exit 1; }

python3 build_scripts/create_deb.py

# Copy .deb to dist/
DEB_FILE=$(find build/ -maxdepth 1 -name "*.deb" -type f | head -1)
if [ -n "$DEB_FILE" ]; then
    cp "$DEB_FILE" dist/
    echo "✓ dist/$(basename "$DEB_FILE") ($(du -h "$DEB_FILE" | cut -f1))"
fi
