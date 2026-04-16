#!/usr/bin/env python3
"""
Create .deb package for Comic Strip Browser
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Add project root to path to import version
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from version import __version__, DEB_VERSION, DEB_MAINTAINER, DEB_HOMEPAGE, CHANGELOG

def create_deb_package():
    """Create a .deb package for Ubuntu/Debian systems."""
    
    deb_dir = project_root / "build" / f"comic-strip-browser_{DEB_VERSION}_amd64"
    
    # Create directory structure
    dirs_to_create = [
        "DEBIAN",
        "usr/bin",
        "usr/share/applications",
        "usr/share/pixmaps",
        "usr/share/icons/hicolor/256x256/apps",
        "usr/share/doc/comic-strip-browser",
        "usr/share/metainfo"
    ]
    
    for dir_path in dirs_to_create:
        (deb_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Create control file
    control_content = f"""Package: comic-strip-browser
Version: {DEB_VERSION}
Section: graphics
Priority: optional
Architecture: amd64
Maintainer: {DEB_MAINTAINER}
Homepage: {DEB_HOMEPAGE}
Description: Comic Strip Browser - Browse a selection of comic strips
 A standalone PyQt6 application for browsing comic strips from GoComics and Comics Kingdom.
 Features include calendar navigation, caching, and support for 40 popular titles,
 including Calvin and Hobbes, Peanuts, Garfield, Shoe, Pearls Before Swine, Bizarro, and more.
"""

    with open(deb_dir / "DEBIAN" / "control", "w") as f:
        f.write(control_content)

    # Create AppStream metadata file
    # Per AppStream spec, the file must be named after the desktop file ID.
    metainfo_content = """<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
    <id>comic-strip-browser.desktop</id>
    <name>Comic Strip Browser</name>
    <summary>Browse a selection of GoComics.com strips</summary>
    <description>
        <p>A standalone PyQt6 application for browsing comic strips from GoComics and Comics Kingdom. Features include calendar navigation, caching, and support for 40 popular titles,
 including Calvin and Hobbes, Peanuts, Garfield, Shoe, Pearls Before Swine, Bizarro, and more.</p>
    </description>
    <screenshots>
        <screenshot type="default">
            <caption>Comic Strip Browser showing Garfield</caption>
            <image>https://raw.githubusercontent.com/DerLudditus/comic-strip-browser/refs/heads/main/ComicStripBrowser.png</image>
        </screenshot>
    </screenshots>
    <project_license>MIT</project_license>
    <metadata_license>CC0-1.0</metadata_license>
    <url type="homepage">https://github.com/DerLudditus/comic-strip-browser</url>
    <developer_name>Homo Ludditus</developer_name>
    <update_contact>ludditus@etik.com</update_contact>
    <icon type="stock">comic-strip-browser</icon>
    <categories>
        <category>Graphics</category>
        <category>Viewer</category>
    </categories>
    <launchable type="desktop-id">comic-strip-browser.desktop</launchable>
</component>
"""

    with open(deb_dir / "usr" / "share" / "metainfo" / "comic-strip-browser.metainfo.xml", "w") as f:
        f.write(metainfo_content)
    
    # Create postinst script
    postinst_content = """#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi
"""
    postinst_path = deb_dir / "DEBIAN" / "postinst"
    with open(postinst_path, "w") as f:
        f.write(postinst_content)
    os.chmod(postinst_path, 0o755)

    # Create postrm script (clean up on uninstall)
    postrm_content = """#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi
"""
    postrm_path = deb_dir / "DEBIAN" / "postrm"
    with open(postrm_path, "w") as f:
        f.write(postrm_content)
    os.chmod(postrm_path, 0o755)

    # Copy executable
    binary_path = project_root / "dist" / "comic-strip-browser"
    if not binary_path.exists():
        print("✗ Binary not found in dist/")
        return False
    shutil.copy2(binary_path,
                 deb_dir / "usr" / "bin" / "comic-strip-browser")
    os.chmod(deb_dir / "usr" / "bin" / "comic-strip-browser", 0o755)
    
    # Copy desktop file
    if (project_root / "assets" / "comic-strip-browser.desktop").exists():
        shutil.copy2(project_root / "assets" / "comic-strip-browser.desktop",
                     deb_dir / "usr" / "share" / "applications")
    
    # Copy icon to both pixmaps and hicolor theme (GNOME prefers hicolor)
    icon_src = project_root / "initial_transparent_alpha.png"
    if not icon_src.exists():
        icon_src = project_root / "assets" / "comic-strip-browser.png"
    if icon_src.exists():
        shutil.copy2(icon_src, deb_dir / "usr" / "share" / "pixmaps" / "comic-strip-browser.png")
        shutil.copy2(icon_src, deb_dir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / "comic-strip-browser.png")
    
    # Create copyright file
    copyright_content = """Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: comic-strip-browser
Upstream-Contact: Homo Ludditus <DerLudditus@gmail.com>
Source: https://github.com/DerLudditus/comic-strip-browser

Files: *
Copyright: 2025 Homo Ludditus <ludditus@etik.com>
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
"""
    
    with open(deb_dir / "usr" / "share" / "doc" / "comic-strip-browser" / "copyright", "w") as f:
        f.write(copyright_content)
    
    # Create changelog file (from version.py)
    with open(deb_dir / "usr" / "share" / "doc" / "comic-strip-browser" / "changelog", "w") as f:
        f.write(CHANGELOG)
    subprocess.run(["gzip", "-9", str(deb_dir / "usr" / "share" / "doc" / "comic-strip-browser" / "changelog")])
    
    # Build the .deb package
    try:
        result = subprocess.run(["dpkg-deb", "--build", str(deb_dir)], 
                              capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            print("✓ .deb package created successfully!")
            print(f"Package: {deb_dir}.deb")
            return True
        else:
            print("✗ Failed to create .deb package")
            print("STDERR:", result.stderr)
            return False
    except FileNotFoundError:
        print("✗ dpkg-deb not found. Install with: sudo apt install dpkg-dev")
        return False

if __name__ == "__main__":
    create_deb_package()

