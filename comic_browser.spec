# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Comic Strip Browser
Cross-platform configuration for Windows and Linux builds
"""

import sys
import os
from pathlib import Path

# Application metadata
APP_NAME = 'ComicStripBrowser'
APP_VERSION = '1.0.4'
APP_DESCRIPTION = 'A standalone comic strip browser for 15 titles from GoComics.com'
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
]
# Remove None entries
datas = [item for item in datas if item is not None]

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'requests',
    'beautifulsoup4',
    'bs4',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',
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
]

# Binaries to exclude (reduce size)
excludes = [
    'tkinter',
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'PIL',
    'Pillow',
]

# Binaries to exclude to use system libraries instead
# binaries_exclude = [
#     'libQt6*',
#     'Qt6*',
# ]

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
        name='ComicStripBrowser',  # Windows executable name
        debug=debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window on Windows
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
        name='comic-strip-browser',  # Linux executable name (lowercase)
        debug=debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

