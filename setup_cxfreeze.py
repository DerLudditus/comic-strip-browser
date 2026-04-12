"""
cx_Freeze setup script for Comic Strip Browser
Alternative to PyInstaller for Windows builds

Changelog (2026-04-12):
- Fixed: Added PIL/Pillow to packages (used by web_scraper.py)
- Fixed: Added include_files for Qt plugins and binaries on Windows
- Fixed: Added explicit PyQt6.QtNetwork to packages
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
        "PyQt6.QtNetwork",
        "requests",
        "bs4",
        "beautifulsoup4",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "idna",
        # PIL/Pillow - used by web_scraper.py for image format detection
        "PIL",
        "PIL.Image",
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
        "ui.embedded_images",
    ],
    "excludes": [
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "test",
        "unittest",
    ],
    "include_files": [
        # Include assets for icons and images
        ("assets/", "assets/") if __import__('os').path.exists("assets/") else None,
    ],
    "optimize": 2,
}
# Remove None entries
build_exe_options["include_files"] = [
    item for item in build_exe_options["include_files"] if item is not None
]

# On Windows, include Qt platform plugins and DLLs
if sys.platform == "win32":
    import os
    import PyQt6
    pyqt6_path = os.path.dirname(PyQt6.__file__)
    qt_bin_path = os.path.join(pyqt6_path, "Qt6", "bin")
    qt_plugins_path = os.path.join(pyqt6_path, "Qt6", "plugins")

    if os.path.exists(qt_plugins_path):
        # Include platform plugin (essential for Windows)
        platforms_path = os.path.join(qt_plugins_path, "platforms")
        if os.path.exists(platforms_path):
            build_exe_options["include_files"].append(
                (platforms_path, "PyQt6/Qt6/plugins/platforms")
            )
        # Include imageformats plugin (for PNG, JPEG, GIF support)
        imageformats_path = os.path.join(qt_plugins_path, "imageformats")
        if os.path.exists(imageformats_path):
            build_exe_options["include_files"].append(
                (imageformats_path, "PyQt6/Qt6/plugins/imageformats")
            )
        # Include styles plugin
        styles_path = os.path.join(qt_plugins_path, "styles")
        if os.path.exists(styles_path):
            build_exe_options["include_files"].append(
                (styles_path, "PyQt6/Qt6/plugins/styles")
            )

    # Include Qt6 DLLs on Windows
    if os.path.exists(qt_bin_path):
        for dll_name in os.listdir(qt_bin_path):
            if dll_name.endswith('.dll'):
                dll_path = os.path.join(qt_bin_path, dll_name)
                build_exe_options["include_files"].append(
                    (dll_path, "PyQt6/Qt6/bin/" + dll_name)
                )

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
