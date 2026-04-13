# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Comic Strip Browser
Cross-platform configuration for Windows and Linux builds

Changelog:
- Fixed: UPX disabled (corrupts Qt6 DLLs)
- Fixed: PIL/Pillow removed from excludes (used by web_scraper.py)
- Fixed: Added PIL, PIL.Image, io to hiddenimports
- Fixed: Use onefile for Linux, onedir for Windows (via CI --onedir flag)
"""

import sys
import os
from pathlib import Path

# Application metadata
APP_NAME = 'ComicStripBrowser'
APP_VERSION = '1.8.9'
APP_DESCRIPTION = 'A standalone comic strip browser for 20 titles from GoComics.com'
APP_AUTHOR = 'Homo Ludditus <ludditus@etik.com>'

# Build configuration
block_cipher = None
debug = False

# Platform-specific settings
is_windows = sys.platform.startswith('win')
is_linux = sys.platform.startswith('linux')

# Define paths
project_root = Path('.')
main_script = project_root / 'main.py'

# Data files to include
datas = [
    # Include any configuration templates or default files
    ('config.json', '.') if (project_root / 'config.json').exists() else None,
    # Include assets for icons and images
    ('assets', 'assets') if (project_root / 'assets').exists() else None,
    # App icon and placeholder (used by main_window.py and comic_viewer.py)
    ('initial_transparent_alpha.png', '.') if (project_root / 'initial_transparent_alpha.png').exists() else None,
]
# Remove None entries
datas = [item for item in datas if item is not None]

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.QtNetwork',
    'requests',
    'beautifulsoup4',
    'bs4',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',
    # PIL/Pillow - used by web_scraper.py for image format detection
    'PIL',
    'PIL.Image',
    'io',
    # Application modules
    'models',
    'models.data_models',
    'services',
    'services.cache_manager',
    'services.comic_service',
    'services.config_manager',
    'services.date_manager',
    'services.error_handler',
    'services.web_scraper',
    'ui',
    'ui.calendar_widget',
    'ui.comic_controller',
    'ui.comic_selector',
    'ui.comic_viewer',
    'ui.main_window',
    'ui.embedded_images',
]

# Exclude only truly unused heavy packages
excludes = [
    'tkinter',
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'test',
    'unittest',
]

# Analysis configuration
a = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific executable configuration
if is_windows:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='ComicStripBrowser',
        debug=debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,  # CRITICAL: UPX corrupts Qt6 DLLs on Windows
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window on Windows (set to True for debugging)
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/comic-strip-browser.ico' if (project_root / 'assets' / 'comic-strip-browser.ico').exists() else None,
        version='version_info.txt' if (project_root / 'version_info.txt').exists() else None,
    )
else:  # Linux
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='comic-strip-browser',
        debug=debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,  # Disabled for consistency with Windows
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
