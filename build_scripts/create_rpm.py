#!/usr/bin/env python3
"""
Create .rpm package for Comic Strip Browser

Builds a binary RPM from a pre-built executable (no source compilation needed).
This mirrors create_deb.py for consistent cross-platform packaging.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path to import version
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from version import __version__, DEB_MAINTAINER, DEB_HOMEPAGE


def create_rpm_package():
    """Create a binary RPM package using rpmbuild."""

    # Check if rpmbuild is available
    try:
        subprocess.run(["rpmbuild", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("✗ rpmbuild not found. Install with:")
        print("  Debian/Ubuntu: sudo apt install rpm")
        print("  Fedora/RHEL:   sudo dnf install rpm-build")
        return False

    # Check if the binary exists
    binary_path = project_root / "dist" / "comic-strip-browser"
    if not binary_path.exists():
        print(f"✗ Binary not found: {binary_path}")
        print("  Build the binary first with: python3 -m PyInstaller comic_browser.spec")
        return False

    version = __version__
    release = "1"
    arch = "x86_64"
    build_dir = project_root / "build" / "rpm-build"

    # Create RPM build directory structure
    rpm_dirs = [
        build_dir / "BUILD",
        build_dir / "RPMS",
        build_dir / "SOURCES",
        build_dir / "SPECS",
        build_dir / "SRPMS",
    ]
    for d in rpm_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Create source tarball containing the pre-built binary + assets
    source_dir = build_dir / f"comic-strip-browser-{version}"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True)

    # Copy binary
    shutil.copy2(binary_path, source_dir / "comic-strip-browser")
    os.chmod(source_dir / "comic-strip-browser", 0o755)

    # Copy assets
    assets_dir = project_root / "assets"
    if assets_dir.exists():
        shutil.copytree(assets_dir, source_dir / "assets")

    # Copy README and LICENSE if they exist
    for f in ["README.md", "LICENSE"]:
        src = project_root / f
        if src.exists():
            shutil.copy2(src, source_dir / f)

    # Create tarball
    tarball = build_dir / "SOURCES" / f"comic-strip-browser-{version}.tar.gz"
    subprocess.run(
        ["tar", "czf", str(tarball), f"comic-strip-browser-{version}"],
        cwd=str(build_dir),
        check=True,
    )

    # Create RPM spec file (binary packaging only, no source build)
    maintainer_name = DEB_MAINTAINER.split("<")[0].strip()
    maintainer_email = DEB_MAINTAINER.split("<")[1].rstrip(">").strip() if "<" in DEB_MAINTAINER else ""

    spec_content = f"""Name:           comic-strip-browser
Version:        {version}
Release:        {release}.fc43
Summary:        Browse GoComics.com comic strips

License:        MIT
URL:            {DEB_HOMEPAGE}
Source0:        %{{name}}-%{{version}}.tar.gz

BuildArch:      x86_64
# These are system libraries not bundled by PyInstaller.
# All Fedora desktop installs include these by default.
Requires:       libX11 libxcb

%description
A standalone PyQt6 application for browsing comic strips from GoComics.com.
Features include calendar navigation, caching, and support for 15 popular
comic strips including Calvin and Hobbes, Peanuts, Garfield, and more.

%prep
%setup -q

%install
# Binary RPM — no build step, just install the pre-built files
mkdir -p %{{buildroot}}%{{_bindir}}
mkdir -p %{{buildroot}}%{{_datadir}}/applications
mkdir -p %{{buildroot}}%{{_datadir}}/pixmaps
mkdir -p %{{buildroot}}%{{_datadir}}/doc/%{{name}}

install -m 0755 comic-strip-browser %{{buildroot}}%{{_bindir}}/comic-strip-browser

if [ -f assets/comic-strip-browser.desktop ]; then
    install -m 0644 assets/comic-strip-browser.desktop %{{buildroot}}%{{_datadir}}/applications/comic-strip-browser.desktop
fi

if [ -f assets/comic-strip-browser.png ]; then
    install -m 0644 assets/comic-strip-browser.png %{{buildroot}}%{{_datadir}}/pixmaps/comic-strip-browser.png
fi

if [ -f README.md ]; then
    install -m 0644 README.md %{{buildroot}}%{{_datadir}}/doc/%{{name}}/README.md
fi

if [ -f LICENSE ]; then
    install -m 0644 LICENSE %{{buildroot}}%{{_datadir}}/doc/%{{name}}/LICENSE
fi

%files
%{{_bindir}}/comic-strip-browser
%{{_datadir}}/applications/comic-strip-browser.desktop
%{{_datadir}}/pixmaps/comic-strip-browser.png
%{{_datadir}}/doc/%{{name}}/

%changelog
* {datetime.now().strftime('%a %b %d %Y')} {maintainer_name} <{maintainer_email}> - {version}-{release}
- Update to version {version}
"""

    spec_path = build_dir / "SPECS" / "comic-strip-browser.spec"
    with open(spec_path, "w") as f:
        f.write(spec_content)

    # Build the RPM
    print(f"Building RPM v{version}...")
    result = subprocess.run(
        ["rpmbuild", "-bb", "--define", f"_topdir {build_dir}", str(spec_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("✗ RPM build failed!")
        print("STDERR:", result.stderr)
        return False

    # Find the built RPM
    rpm_pattern = build_dir / "RPMS" / arch / f"comic-strip-browser-{version}-*.rpm"
    rpm_files = list(build_dir.glob(f"RPMS/{arch}/comic-strip-browser-{version}-*.rpm"))

    if not rpm_files:
        print("✗ RPM file not found after build!")
        return False

    rpm_path = rpm_files[0]
    print(f"✓ RPM package created: {rpm_path}")
    print(f"  Size: {rpm_path.stat().st_size / (1024*1024):.1f} MB")

    # Copy to releases directory
    releases_dir = project_root / "releases"
    releases_dir.mkdir(exist_ok=True)
    dest = releases_dir / rpm_path.name
    shutil.copy2(rpm_path, dest)
    print(f"  Copied to: {dest}")

    return True


if __name__ == "__main__":
    success = create_rpm_package()
    sys.exit(0 if success else 1)
