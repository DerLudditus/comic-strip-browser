"""
Comic Strip Browser - Version Information

This is the single source of truth for version information.
Update this file when releasing a new version.
"""

__version__ = "2.4.0"
__version_info__ = (2, 4, 0)

# Release information
RELEASE_DATE = "2026-04-19"
RELEASE_NAME = "Comic Strip Browser"

# Package information for .deb
DEB_VERSION = "2.3.2-1"
DEB_MAINTAINER = "Homo Ludditus <DerLudditus@gmail.com>"
DEB_HOMEPAGE = "https://github.com/DerLudditus/comic-strip-browser"

# Changelog entry (most recent first)
CHANGELOG = """comic-strip-browser (2.4.0-1) stable; urgency=medium
  * Simplified the scaling down of huge comics. 
  * Defined the gaps in Calvin and Hobbes.
  * Pluggers is now retrieved from both sites (just like Shoe). There are differences in availability and colors.
  * Added Mutts, thus increasing to 42 the titles (40 unique, as Shoe and Pluggers are twice).

 -- Homo Ludditus <DerLudditus@gmail.com>  Sun, 19 Apr 2026 08:30 +0300
 
comic-strip-browser (2.3.2-1) stable; urgency=medium
  * Fix AppImage not being able to open the cache folder using the button.

 -- Homo Ludditus <DerLudditus@gmail.com>  Sun, 19 Apr 2026 01:20 +0300
 
comic-strip-browser (2.3.1-1) stable; urgency=medium
  * Cosmetic fix: bold was heavier under KDE because of applying the bold attribute twice: setBold and setStyleSheet (XFCE/GNOME ignored bold-over-bold).

 -- Homo Ludditus <DerLudditus@gmail.com>  Sun, 19 Apr 2026 00:42 +0300
 
comic-strip-browser (2.3.0-1) stable; urgency=medium
  * Major release with speed improvements, better error handling, code cleanup and small fixes.
  * Known gaps in comic strips availability addressed, so the calendar will be gray for such days, and Random will skip them.

 -- Homo Ludditus <DerLudditus@gmail.com>  Sun, 19 Apr 2026 00:23 +0300
 
comic-strip-browser (2.2.2-1) stable; urgency=medium
  * Interim release to test fixing REGRESSIONS introduced in 2.2.0.

 -- Homo Ludditus <DerLudditus@gmail.com>  Sat, 18 Apr 2026 14:25 +0300
 
comic-strip-browser (2.2.0-1) stable; urgency=medium
  * Several functionality improvements and bug fixes.
  * Some bugs remain.

 -- Homo Ludditus <DerLudditus@gmail.com>  Fri, 17 Apr 2026 03:25 +0300
 
comic-strip-browser (2.1.0-1) stable; urgency=medium
  * Fixed "Previous", "Next" or "Random" buttons not triggering "Loading comic..." and "Downloading comic image..." feedback.
  * Fixed the missing update-desktop-database.

 -- Homo Ludditus <DerLudditus@gmail.com>  Fri, 17 Apr 2026 01:05 +0300
 
comic-strip-browser (2.0.7-1) stable; urgency=medium
  * This should really fix the initial wait cursor on Wayland.

 -- Homo Ludditus <DerLudditus@gmail.com>  Thu, 16 Apr 2026 23:47:00 +0300
 
comic-strip-browser (2.0.6-1) stable; urgency=medium
  * If this doesn't fix the initial wait cursor on Wayland, I don't know what else would do it.

 -- Homo Ludditus <DerLudditus@gmail.com>  Thu, 16 Apr 2026 23:06:00 +0300
 
comic-strip-browser (2.0.5-1) stable; urgency=medium
  * Cleanup of the code regarding the calendar widget.

 -- Homo Ludditus <DerLudditus@gmail.com>  Thu, 16 Apr 2026 22:20:00 +0300
 
comic-strip-browser (2.0.4-1) stable; urgency=medium
  * Really fix the initial busy cursor on Wayland.  

 -- Homo Ludditus <DerLudditus@gmail.com>  Thu, 16 Apr 2026 21:30:00 +0300
 
comic-strip-browser (2.0.3-1) stable; urgency=medium
  * Fix the initial busy cursor on Wayland.  

 -- Homo Ludditus <DerLudditus@gmail.com>  Thu, 16 Apr 2026 21:12:00 +0300
 
comic-strip-browser (2.0.2-1) stable; urgency=medium
  * Small adjustments of background colors.  

 -- Homo Ludditus <DerLudditus@gmail.com>  Tue, 14 Apr 2026 21:30:00 +0300
 
comic-strip-browser (2.0.1-1) stable; urgency=medium
  * Force light backgrounds even on dark-themed systems.  

 -- Homo Ludditus <DerLudditus@gmail.com>  Tue, 14 Apr 2026 20:20:00 +0300

comic-strip-browser (2.0.0-1) stable; urgency=medium
  * Major redesign to add Comics Kingdom 
  * 40 comic strip titles are now supported  
  * Better handling of errors
  * More informative error messages
  * Many bug fixes
  * Many bugs still present (or new bugs added)

 -- Homo Ludditus <DerLudditus@gmail.com>  Tue, 14 Apr 2026 20:00:00 +0300

comic-strip-browser (1.9.0-1) stable; urgency=medium
  * Improved displaying on fractional scaling (DPR-aware rendering)
  * Windows builds now produce a single onefile EXE
  * Updated GitHub Actions to Node.js 24 compatible actions
  * Fixed: 15 → 20 comic strips in package metadata

 -- Homo Ludditus <ludditus@etik.com>  Mon, 13 Apr 2026 05:00:00 +0300

comic-strip-browser (1.1.3-1) stable; urgency=medium
  * Removed Wizard of Id Classics because GoComics stopped publishing it on Oct. 31 (it was a reprint, anyway)
  * Number of strip titles: 20

 -- Homo Ludditus <ludditus@etik.com>  Fri, 14 Nov 2025 22:25:00 +0300

comic-strip-browser (1.1.2-1) stable; urgency=medium
  * Added 6 more comic strip titles, to a total of 21

 -- Homo Ludditus <ludditus@etik.com>  Fri, 14 Nov 2025 08:25:00 +0300

comic-strip-browser (1.1.1-1) stable; urgency=medium
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
