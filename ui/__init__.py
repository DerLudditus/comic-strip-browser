# UI package for comic strip browser

from typing import List
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


def get_font_families() -> List[str]:
    """Include 'Noto Color Emoji' right after the text fonts so that Qt's
    glyph-level font fallback renders emoji characters in color on Qt < 6.11.
    """
    app = QApplication.instance()
    system_family = app.font().family() if app else ""

    fallback_list = [
        system_family,
        "Noto Sans",
        "Noto Color Emoji",      # Emoji fallback (Linux)
        "Segoe UI",
        "Segoe UI Emoji",        # Emoji fallback (Windows)
        "Apple Color Emoji",     # Emoji fallback (macOS)
        "Open Sans",
        "DejaVu Sans",
        "Arial",
        "sans-serif",
    ]
    return list(dict.fromkeys(filter(None, fallback_list)))


def get_bold_weight() -> QFont.Weight:
    """Forcing everything bold to be semibold if the variant exists.
    Qt6 should automatically use the bold (weight 700) variant if 
    the default font doesn't have a semibold (weight 600) variant.
    """
    return QFont.Weight.DemiBold