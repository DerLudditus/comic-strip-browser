#!/bin/bash
# Build .rpm package (Fedora/RHEL only)
# Usage: ./build_scripts/build_rpm.sh
# Requires: build_binary.sh run first

set -e
cd "$(dirname "$0")/.."

echo "=== Comic Strip Browser — .rpm Build ==="

command -v rpmbuild &>/dev/null || { echo "✗ rpmbuild not found — install rpm-build"; exit 1; }

BINARY="dist/comic-strip-browser"
[ -f "$BINARY" ] || { echo "✗ Binary not found — run build_binary.sh first"; exit 1; }

VERSION=$(python3 -c "from version import __version__; print(__version__)")
RELEASE="1"

RPMBUILD="$HOME/rpmbuild"
mkdir -p "$RPMBUILD"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

# Create tarball (binary + desktop + icon + LICENSE/README)
TMPDIR=$(mktemp -d)
SRCDIR="$TMPDIR/comic-strip-browser-$VERSION"
mkdir -p "$SRCDIR"

cp "$BINARY" "$SRCDIR/comic-strip-browser"
chmod +x "$SRCDIR/comic-strip-browser"
[ -f assets/comic-strip-browser.desktop ] && cp assets/comic-strip-browser.desktop "$SRCDIR/"
ICON_SRC="initial_transparent_alpha.png"
[ ! -f "$ICON_SRC" ] && ICON_SRC="assets/comic-strip-browser.png"
[ -f "$ICON_SRC" ] && cp "$ICON_SRC" "$SRCDIR/comic-strip-browser.png"
[ -f LICENSE ] && cp LICENSE "$SRCDIR/"
[ -f README.md ] && cp README.md "$SRCDIR/"

cd "$TMPDIR" && tar czf "$RPMBUILD/SOURCES/comic-strip-browser-$VERSION.tar.gz" "comic-strip-browser-$VERSION"
cd - >/dev/null
rm -rf "$TMPDIR"

# Generate spec
SPEC="$RPMBUILD/SPECS/comic-strip-browser.spec"
cat > "$SPEC" << EOF
Name:           comic-strip-browser
Version:        $VERSION
Release:        $RELEASE
Summary:        A standalone comic strip browser for GoComics and Comics Kingdom
License:        MIT
URL:            https://github.com/DerLudditus/comic-strip-browser
Source0:        %{name}-%{version}.tar.gz
BuildArch:      x86_64

%description
A standalone PyQt6 application for browsing comic strips from GoComics and Comics Kingdom.

%prep
%autosetup

%build

%install
install -D -m 0755 %{name} %{buildroot}%{_bindir}/%{name}
[ -f %{name}.desktop ] && install -D -m 0644 %{name}.desktop %{buildroot}%{_datadir}/applications/%{name}.desktop
[ -f %{name}.png ] && install -D -m 0644 %{name}.png %{buildroot}%{_datadir}/pixmaps/%{name}.png
[ -f %{name}.png ] && install -D -m 0644 %{name}.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/%{name}.png

%files
%{_bindir}/%{name}
%{_datadir}/applications/%{name}.desktop
%{_datadir}/pixmaps/%{name}.png
%{_datadir}/icons/hicolor/256x256/apps/%{name}.png

%post
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database %{_datadir}/applications
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t %{_datadir}/icons/hicolor 2>/dev/null || true
fi

%postun
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database %{_datadir}/applications
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t %{_datadir}/icons/hicolor 2>/dev/null || true
fi

%changelog
* $(date +"%a %b %d %Y") Homo Ludditus <DerLudditus@gmail.com> - ${VERSION}-${RELEASE}
- Release $VERSION
EOF

echo "Running rpmbuild..."
rpmbuild -bb "$SPEC"

RPM_PATH=$(ls "$RPMBUILD/RPMS/x86_64"/comic-strip-browser-${VERSION}-*.x86_64.rpm 2>/dev/null || echo "")
if [ -n "$RPM_PATH" ]; then
    cp "$RPM_PATH" dist/
    echo "✓ dist/$(basename "$RPM_PATH") ($(du -h "$RPM_PATH" | cut -f1))"
else
    echo "✗ RPM not found"; exit 1
fi
