# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Comic Strip Browser - ONEDIR mode
Recommended for Windows builds: bundles Qt6 DLLs as separate files
instead of embedding in a single EXE, which is more reliable.

To build:
    python -m PyInstaller comic_browser_onedir.spec --clean --noconfirm

The output will be dist/comic-browser/ directory containing the EXE + DLLs.
"""

import sys
import os
from pathlib import Path

# Application metadata
APP_NAME = 'ComicStripBrowser'
APP_VERSION = '1.1.2'

# Build configuration
block_cipher = None
debug = False

is_windows = sys.platform.startswith('win')
is_linux = sys.platform.startswith('linux')

project_root = Path('.')
main_script = project_root / 'main.py'

# Data files to include
datas = [
    ('config.json', '.') if (project_root / 'config.json').exists() else None,
    ('assets', 'assets') if (project_root / 'assets').exists() else None,
]
datas = [item for item in datas if item is not None]

# Hidden imports - all modules PyInstaller might miss
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

# Analysis
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

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ONEDIR: creates a directory with EXE + DLLs + dependencies
if is_windows:
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,  # ONEDIR: binaries go to separate folder
        name='ComicStripBrowser',
        debug=debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,  # CRITICAL: UPX corrupts Qt6 DLLs on Windows
        upx_exclude=[],
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/comic-strip-browser.ico' if (project_root / 'assets' / 'comic-strip-browser.ico').exists() else None,
        version='version_info.txt' if (project_root / 'version_info.txt').exists() else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='ComicStripBrowser',
    )
else:  # Linux
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name='comic-strip-browser',
        debug=debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='comic-strip-browser',
    )
