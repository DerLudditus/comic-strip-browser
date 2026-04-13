#!/bin/bash
# Build AppImage from the pre-built onefile binary
# Usage: ./build_scripts/build_appimage.sh
# Requires: build_binary.sh run first

set -e
cd "$(dirname "$0")/.."

echo "=== Comic Strip Browser — AppImage Build ==="

BINARY="dist/comic-strip-browser"
[ -f "$BINARY" ] || { echo "✗ Binary not found — run build_binary.sh first"; exit 1; }

VERSION=$(python3 -c "from version import __version__; print(__version__)")
APPIMAGE="dist/comic-strip-browser-${VERSION}.AppImage"
APPDIR="build/ComicStripBrowser.AppDir"
TOOL="appimagetool-x86_64.AppImage"

rm -rf "$APPDIR"
mkdir -p "$APPDIR"/{usr/bin,usr/share/applications,usr/share/pixmaps}

cp "$BINARY" "$APPDIR/usr/bin/comic-strip-browser"
chmod +x "$APPDIR/usr/bin/comic-strip-browser"
ln -sf usr/bin/comic-strip-browser "$APPDIR/AppRun"

[ -f assets/comic-strip-browser.desktop ] && cp assets/comic-strip-browser.desktop "$APPDIR/"

ICON_SRC="initial_transparent_alpha.png"
[ ! -f "$ICON_SRC" ] && ICON_SRC="assets/comic-strip-browser.png"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$APPDIR/comic-strip-browser.png"
    cp "$ICON_SRC" "$APPDIR/.DirIcon"
    cp "$ICON_SRC" "$APPDIR/usr/share/pixmaps/comic-strip-browser.png"
fi

[ -f "$TOOL" ] || {
    echo "Downloading appimagetool..."
    wget -q -O "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
}

echo "Creating AppImage..."
ARCH=x86_64 "./$TOOL" "$APPDIR" "$APPIMAGE"

echo "✓ $APPIMAGE ($(du -h "$APPIMAGE" | cut -f1))"
