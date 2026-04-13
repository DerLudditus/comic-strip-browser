# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Comic Strip Browser
Both Linux and Windows: onefile (single large binary)
"""

import sys
from pathlib import Path

project_root = Path('.')

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

is_windows = sys.platform.startswith('win')

a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
)

pyz = PYZ(a.pure, a.zipped_data)

# ── Windows: onefile ──
if is_windows:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name='ComicStripBrowser',
        console=False, upx=False, strip=False,
        icon='assets/comic-strip-browser.ico' if (project_root / 'assets' / 'comic-strip-browser.ico').exists() else None,
    )
# ── Linux: onefile ──
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name='comic-strip-browser',
        console=False, upx=False, strip=False,
    )
