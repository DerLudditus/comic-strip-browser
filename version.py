"""
Comic Strip Browser - Version Information

This is the single source of truth for version information.
Update this file when releasing a new version.
"""

__version__ = "1.1.1"
__version_info__ = (1, 1, 1)

# Release information
RELEASE_DATE = "2025-10-21"
RELEASE_NAME = "Comic Strip Browser"

# Package information for .deb
DEB_VERSION = "1.1.1-1"
DEB_MAINTAINER = "Homo Ludditus <ludditus@etik.com>"
DEB_HOMEPAGE = "https://github.com/DerLudditus/comic-strip-browser"

# Changelog entry (most recent first)
CHANGELOG = """comic-strip-browser (1.1.1-1) stable; urgency=medium
  * Updated the start dates of each comic regarding their presence on GoComics
  * Added "First" and "Random" buttons for navigation
  * Added smart Next/Previous navigation that skips gaps
  * Added global keyboard shortcuts (Left/Right arrows: Previous/Next, Home/End: First/Today)
  * Fixed image format detection (now detects PNG/GIF correctly, so cached files have the correct extension)
  * Improved performance
  * Fixed the status bar
  * Removed the logging
  * Various UI improvements and bug fixes
  * Race conditions could still made the app "forget" the currently selected comic title on occasions

 -- Homo Ludditus <ludditus@etik.com>  Tue, 21 Oct 2025 12:00:00 +0300

comic-strip-browser (1.0.4-1) stable; urgency=medium

  * Added the 15th comic strip title

 -- Homo Ludditus <ludditus@etik.com>  Fri, 25 Jul 2025 03:15:00 +0300
"""
