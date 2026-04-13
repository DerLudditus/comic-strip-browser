# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Comic Strip Browser
Linux: onefile (single ~70 MB binary)
Windows: onedir (directory with DLLs)
"""

import sys
import os
from pathlib import Path

# Platform-specific settings
is_windows = sys.platform.startswith('win')
is_linux = sys.platform.startswith('linux')

project_root = Path('.')

# Data files to include
datas = [
    ('assets', 'assets') if (project_root / 'assets').exists() else None,
    ('initial_transparent_alpha.png', '.') if (project_root / 'initial_transparent_alpha.png').exists() else None,
]
datas = [item for item in datas if item is not None]

hiddenimports = [
    'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 'PyQt6.QtNetwork',
    'requests', 'beautifulsoup4', 'bs4', 'urllib3', 'certifi',
    'charset_normalizer', 'idna', 'PIL', 'PIL.Image', 'io',
    'models', 'models.data_models',
    'services.cache_manager', 'services.comic_service', 'services.config_manager',
    'services.date_manager', 'services.error_handler', 'services.web_scraper',
    'ui.calendar_widget', 'ui.comic_controller', 'ui.comic_selector',
    'ui.comic_viewer', 'ui.main_window', 'ui.embedded_images',
]

excludes = ['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'test', 'unittest']

a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    cipher=None,
)

pyz = PYZ(a.pure, a.zipped_data)

# Platform-specific output
if is_windows:
    # ── Windows: onedir ──
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name='ComicStripBrowser',
        console=False, upx=False,
        icon='assets/comic-strip-browser.ico' if (project_root / 'assets' / 'comic-strip-browser.ico').exists() else None,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        name='ComicStripBrowser',
    )
else:
    # ── Linux: onefile ──
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name='comic-strip-browser',
        console=False, upx=False,
    )
