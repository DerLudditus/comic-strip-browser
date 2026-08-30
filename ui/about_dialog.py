"""
About dialog for Comic Strip Browser.
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QIcon

from version import __version__
from ui import get_font_families, get_bold_weight


class AboutDialog(QDialog):
    """Simple about dialog with app info, logo, and GitHub link."""

    GITHUB_URL = "https://github.com/DerLudditus/comic-strip-browser"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Comic Strip Browser")
        self.setFixedSize(440, 460)
        self.setModal(True)

        # Set dialog icon if available
        assets_icon = Path(__file__).parent.parent / "assets" / "comic-strip-browser.png"
        if assets_icon.exists():
            self.setWindowIcon(QIcon(str(assets_icon)))

        self._build_ui()
        self.setStyleSheet("""
            QDialog {
                background-color: #e8e8e8;
            }
            QLabel {
                color: #000000;
                background-color: transparent;
            }
        """)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # App name
        name_label = QLabel("Comic Strip Browser")
        name_font = QFont()
        name_font.setPointSize(18)
        name_font.setWeight(get_bold_weight())
        name_font.setFamilies(get_font_families())
        name_label.setStyleSheet("border:none")
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # Version
        ver_label = QLabel(f"Version {__version__}")
        ver_font = QFont()
        ver_font.setPointSize(13)
        ver_font.setWeight(get_bold_weight())
        ver_font.setFamilies(get_font_families())
        ver_label.setFont(ver_font)
        ver_label.setStyleSheet("border:none")
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_label)

        # Logo / Mascot image
        assets_icon = Path(__file__).parent.parent / "assets" / "comic-strip-browser.png"
        if assets_icon.exists():
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(str(assets_icon))
            if not pixmap.isNull():
                dpr = self.devicePixelRatioF() if self.devicePixelRatioF() >= 1.0 else 1.0
                logical_size = 200
                physical_size = max(1, int(logical_size * dpr))

                scaled_pixmap = pixmap.scaled(
                    physical_size, physical_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                scaled_pixmap.setDevicePixelRatio(dpr)

                image_label.setPixmap(scaled_pixmap)
                image_label.setFixedSize(logical_size, logical_size)
            image_label.setStyleSheet("border:none; background: transparent;")
            layout.addWidget(image_label, 0, Qt.AlignmentFlag.AlignHCenter)

        # Description
        desc_label = QLabel(
            "Browse daily comic strips from\n"
            "GoComics.com & ComicsKingdom.com\n"
            "with calendar navigation and offline caching."
        )
        desc_font = QFont()
        desc_font.setPointSize(12)
        desc_font.setFamilies(get_font_families())
        desc_font.setWeight(get_bold_weight())
        desc_label.setFont(desc_font)
        desc_label.setStyleSheet("border:none; background: transparent;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # GitHub link
        link_label = QLabel(
            '<a href="{url}" style="color:#0d6efd; text-decoration:none;">'
            'Source on GitHub</a>'.format(url=self.GITHUB_URL)
        )
        link_font = QFont()
        link_font.setPointSize(12)
        link_font.setWeight(get_bold_weight())
        link_font.setFamilies(get_font_families())
        link_label.setStyleSheet("border:none")
        link_label.setFont(link_font)
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setTextFormat(Qt.TextFormat.RichText)
        link_label.setOpenExternalLinks(True)
        layout.addWidget(link_label)

        layout.addStretch()

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        # close_btn.setFixedSize(80, 30)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
