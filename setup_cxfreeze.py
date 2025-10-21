"""
cx_Freeze setup script for Comic Strip Browser
Alternative to PyInstaller for Windows builds
"""

import sys
from cx_Freeze import setup, Executable
from version import __version__, DEB_MAINTAINER

# Dependencies are automatically detected, but some modules need help
build_exe_options = {
    "packages": [
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtWidgets",
        "PyQt6.QtGui",
        "requests",
        "bs4",
        "beautifulsoup4",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "idna",
    ],
    "includes": [
        "models.data_models",
        "services.cache_manager",
        "services.comic_service",
        "services.config_manager",
        "services.date_manager",
        "services.error_handler",
        "services.web_scraper",
        "ui.calendar_widget",
        "ui.comic_controller",
        "ui.comic_selector",
        "ui.comic_viewer",
        "ui.main_window",
    ],
    "excludes": [
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "PIL",
        "Pillow",
        "test",
        "unittest",
    ],
    "include_files": [
        # Add any additional files here if needed
        # ("assets/", "assets/"),
    ],
    "optimize": 2,
}

# Base for Windows GUI application (no console window)
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# Executable configuration
executables = [
    Executable(
        "main.py",
        base=base,
        target_name="ComicStripBrowser.exe",
        icon="assets/comic-strip-browser.ico" if sys.platform == "win32" else None,
        shortcut_name="Comic Strip Browser",
        shortcut_dir="DesktopFolder",
    )
]

# Setup configuration
setup(
    name="ComicStripBrowser",
    version=__version__,
    description="A standalone comic strip browser for 15 titles from GoComics.com",
    author=DEB_MAINTAINER.split("<")[0].strip(),
    options={"build_exe": build_exe_options},
    executables=executables,
)
