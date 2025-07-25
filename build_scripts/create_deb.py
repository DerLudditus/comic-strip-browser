#!/usr/bin/env python3
"""
Create .deb package for Comic Strip Browser
"""

import os
import shutil
import subprocess
from pathlib import Path

def create_deb_package():
    """Create a .deb package for Ubuntu/Debian systems."""
    
    project_root = Path(__file__).parent.parent
    deb_dir = project_root / "build" / "comic-strip-browser_1.0.4-1_amd64"
    
    # Create directory structure
    dirs_to_create = [
        "DEBIAN",
        "usr/bin",
        "usr/share/applications",
        "usr/share/pixmaps",
        "usr/share/doc/comic-strip-browser",
        "usr/share/metainfo"
    ]
    
    for dir_path in dirs_to_create:
        (deb_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Create control file
    control_content = """Package: comic-strip-browser
Version: 1.0.4-1
Section: graphics
Priority: optional
Architecture: amd64
Maintainer: Homo Ludditus <ludditus@etik.com>
Homepage: https://github.com/DerLudditus/comic-strip-browser
Description: Comic Strip Browser - Browse a selection of GoComics.com strips
 A standalone PyQt6 application for browsing comic strips from GoComics.com.
 Features include calendar navigation, caching, and support for 15 popular
 comic strips including Calvin and Hobbes, Peanuts, Garfield, and more.
"""
    
    with open(deb_dir / "DEBIAN" / "control", "w") as f:
        f.write(control_content)
    
    # Create AppStream metadata file
    metainfo_content = """<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
    <id>io.github.DerLudditus.ComicStripBrowser</id>
    <name>Comic Strip Browser</name>
    <summary>Browse a selection of GoComics.com strips</summary>
    <description>
        <p>A standalone PyQt6 application for browsing comic strips from GoComics.com. Features include calendar navigation, caching, and support for 15 popular comic strips including Calvin and Hobbes, Peanuts, Garfield, and more.</p>
    </description>
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
    
    # Copy executable
    shutil.copy2(project_root / "dist" / "comic-strip-browser", 
                 deb_dir / "usr" / "bin" / "comic-strip-browser")
    os.chmod(deb_dir / "usr" / "bin" / "comic-strip-browser", 0o755)
    
    # Copy desktop file
    if (project_root / "assets" / "comic-strip-browser.desktop").exists():
        shutil.copy2(project_root / "assets" / "comic-strip-browser.desktop",
                     deb_dir / "usr" / "share" / "applications")
    
    # Copy icon
    if (project_root / "assets" / "comic-strip-browser.png").exists():
        shutil.copy2(project_root / "assets" / "comic-strip-browser.png",
                     deb_dir / "usr" / "share" / "pixmaps" / "comic-strip-browser.png")
    
    # Create copyright file
    copyright_content = """Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: comic-strip-browser
Upstream-Contact: Homo Ludditus <ludditus@etik.com>
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
    
    # Create changelog file
    changelog_content = """comic-strip-browser (1.0.4-1) stable; urgency=medium

  * Added the 15th comic strip title

 -- Homo Ludditus <ludditus@etik.com>  Fri, 25 Jul 2025 03:15:00 +0300
"""
    
    with open(deb_dir / "usr" / "share" / "doc" / "comic-strip-browser" / "changelog", "w") as f:
        f.write(changelog_content)
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

