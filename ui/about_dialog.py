"""
About dialog for Comic Strip Browser.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtCore import QUrl

from version import __version__


class AboutDialog(QDialog):
    """Simple about dialog with app info and GitHub link."""

    GITHUB_URL = "https://github.com/DerLudditus/comic-strip-browser"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Comic Strip Browser")
        self.setFixedSize(420, 320)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        # App name
        name_label = QLabel("Comic Strip Browser")
        name_font = QFont()
        name_font.setPointSize(18)
        name_font.setBold(True)
        name_font.setFamilies(["Noto Sans", "Segoe UI", "Arial", "sans-serif"])
        name_label.setStyleSheet("color: #000000; font-weight: bold; border:none") 
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # Version
        ver_label = QLabel(f"Version {__version__}")
        ver_font = QFont()
        ver_font.setPointSize(13)
        ver_font.setFamilies(["Noto Sans", "Segoe UI", "Arial", "sans-serif"])
        ver_label.setFont(ver_font)
        ver_label.setStyleSheet("color: #000000; font-weight: bold; border:none")         
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_label)

        # Description
        desc_label = QLabel(
            "Browse 40 daily comic strips from\n"
            "GoComics.com & ComicsKingdom.com\n"
            "with offline caching and calendar navigation."
        )
        desc_font = QFont()
        desc_font.setPointSize(12)
        desc_font.setFamilies(["Noto Sans", "Segoe UI", "Arial", "sans-serif"])
        desc_font.setBold(True)
        desc_label.setContentsMargins(24, 20, 24, 16)
        desc_label.setFont(desc_font)
        desc_label.setStyleSheet("color: #000000; font-weight: bold; border:none")         
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #000000;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # GitHub link
        link_label = QLabel(
            '<a href="{url}" style="color:#0d6efd; text-decoration:none;">'
            ' Source on GitHub</a>'.format(url=self.GITHUB_URL)
        )
        link_font = QFont()
        link_font.setPointSize(12)
        link_font.setBold(True)
        link_font.setFamilies(["Noto Sans", "Segoe UI", "Arial", "sans-serif"])
        link_label.setStyleSheet("color: #000000; font-weight: bold; border:none")         
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
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
