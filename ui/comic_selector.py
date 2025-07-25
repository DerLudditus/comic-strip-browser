"""
Comic selector UI component for the Comic Strip Browser application.

This module contains the ComicSelector widget which provides a list/menu interface
for selecting from the 15 available comic strips, displaying comic metadata,
and handling selection events.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPalette

from models.data_models import COMIC_DEFINITIONS, ComicDefinition


class ComicSelectorItem(QWidget):
    """
    Custom widget for displaying individual comic strip information in the selector.
    
    This widget shows the comic's display name, author, and provides visual
    feedback for selection state.
    """
    
    def __init__(self, comic_definition: ComicDefinition):
        """
        Initialize the comic selector item.
        
        Args:
            comic_definition: ComicDefinition object containing comic metadata
        """
        super().__init__()
        self.comic_definition = comic_definition
        self.is_selected = False
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI layout and styling for the comic item."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(2)
        
        # Comic display name
        self.name_label = QLabel(self.comic_definition.display_name)
        name_font = QFont()
        name_font.setPointSize(11)
        name_font.setBold(True)
        self.name_label.setFont(name_font)
        self.name_label.setStyleSheet("color: #000000; font-weight: bold;")  # Ensure black text and bold
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)
        
        # Author information
        self.author_label = QLabel(f"by {self.comic_definition.author}")
        author_font = QFont()
        author_font.setPointSize(9)
        author_font.setItalic(True)
        self.author_label.setFont(author_font)
        self.author_label.setStyleSheet("color: #666666;")
        self.author_label.setWordWrap(True)
        layout.addWidget(self.author_label)
        
        # Set initial styling
        self.update_selection_style()
    
    def set_selected(self, selected: bool):
        """
        Set the selection state of this comic item.
        
        Args:
            selected: True if this item should be selected
        """
        self.is_selected = selected
        self.update_selection_style()
    
    def update_selection_style(self):
        """Update the visual styling based on selection state."""
        if self.is_selected:
            self.setStyleSheet("""
                ComicSelectorItem {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 6px;
                }
            """)
            # Ensure name label styling is preserved
            self.name_label.setStyleSheet("color: #000000; font-weight: bold;")
        else:
            self.setStyleSheet("""
                ComicSelectorItem {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                }
                ComicSelectorItem:hover {
                    background-color: #f5f5f5;
                    border: 1px solid #bdbdbd;
                }
            """)
            # Ensure name label styling is preserved
            self.name_label.setStyleSheet("color: #000000; font-weight: bold;")
    
    def mousePressEvent(self, event):
        """Handle mouse press events for selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Emit selection through parent widget
            parent = self.parent()
            while parent and not isinstance(parent, ComicSelector):
                parent = parent.parent()
            if parent:
                parent.select_comic_item(self)
        super().mousePressEvent(event)


class ComicSelector(QWidget):
    """
    Comic strip selection interface widget.
    
    Responsibilities:
    - Display list of available comics with metadata
    - Handle comic selection and emit events
    - Provide visual feedback for selected comic
    - Style the selector with proper spacing and visual hierarchy
    """
    
    # Signal emitted when a comic is selected
    comic_selected = pyqtSignal(str)  # Emits comic name
    
    def __init__(self, parent=None):
        """Initialize the comic selector widget."""
        super().__init__(parent)
        self.comic_items = {}  # Maps comic name to ComicSelectorItem
        self.selected_comic = None
        self.setup_ui()
        self.populate_comic_list()
    
    def setup_ui(self):
        """Set up the main UI layout and components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Set gray background for the entire widget to work with dark themes
        self.setStyleSheet("""
            ComicSelector {
                background-color: #e0e0e0;
            }
        """)
        
        # Header section
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.NoFrame)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #e0e0e0;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(4, 2, 4, 2)
        
        # Title
        title_label = QLabel("Comic Strips")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #000000; font-weight: bold;")  # Ensure black text and bold
        header_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Select a strip to browse")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_font.setBold(True)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #000000; font-weight: bold;")  # Make it bold and dark
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_frame)
        
        # Scrollable comic list area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #e0e0e0;
            }
        """)
        
        # Container widget for comic items
        self.comics_container = QWidget()
        self.comics_container.setStyleSheet("""
            QWidget {
                background-color: #e0e0e0;
            }
        """)
        self.comics_layout = QVBoxLayout(self.comics_container)
        self.comics_layout.setContentsMargins(4, 4, 4, 4)
        self.comics_layout.setSpacing(3)
        
        scroll_area.setWidget(self.comics_container)
        layout.addWidget(scroll_area)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    
    def populate_comic_list(self):
        """Load and display all available comic strips."""
        # Clear existing items
        self.comic_items.clear()
        
        # Add each comic definition as a selectable item
        for comic_def in COMIC_DEFINITIONS:
            comic_item = ComicSelectorItem(comic_def)
            self.comic_items[comic_def.name] = comic_item
            self.comics_layout.addWidget(comic_item)
        
        # Add stretch to push items to the top
        self.comics_layout.addStretch()
        
        # Select the first comic by default
        if COMIC_DEFINITIONS:
            self.select_comic(COMIC_DEFINITIONS[0].name)
    
    def select_comic(self, comic_name: str):
        """
        Select a comic by name and update the UI.
        
        Args:
            comic_name: Name of the comic to select
        """
        if comic_name not in self.comic_items:
            return
        
        # Deselect previously selected comic
        if self.selected_comic and self.selected_comic in self.comic_items:
            self.comic_items[self.selected_comic].set_selected(False)
        
        # Select new comic
        self.selected_comic = comic_name
        self.comic_items[comic_name].set_selected(True)
        
        # Emit selection signal
        self.comic_selected.emit(comic_name)
    
    def select_comic_item(self, comic_item: ComicSelectorItem):
        """
        Select a comic by its item widget.
        
        Args:
            comic_item: ComicSelectorItem that was clicked
        """
        self.select_comic(comic_item.comic_definition.name)
    
    def get_selected_comic(self) -> str:
        """
        Get the currently selected comic name.
        
        Returns:
            Name of the currently selected comic, or None if none selected
        """
        return self.selected_comic
    
    def get_selected_comic_definition(self) -> ComicDefinition:
        """
        Get the ComicDefinition for the currently selected comic.
        
        Returns:
            ComicDefinition object for selected comic, or None if none selected
        """
        if not self.selected_comic:
            return None
        
        for comic_def in COMIC_DEFINITIONS:
            if comic_def.name == self.selected_comic:
                return comic_def
        return None
    
    def set_comic_availability(self, comic_name: str, available: bool):
        """
        Set the availability status of a comic (for future use).
        
        Args:
            comic_name: Name of the comic
            available: Whether the comic is currently available
        """
        if comic_name in self.comic_items:
            item = self.comic_items[comic_name]
            if available:
                item.setEnabled(True)
                item.setStyleSheet(item.styleSheet().replace("color: #cccccc;", ""))
            else:
                item.setEnabled(False)
                item.setStyleSheet(item.styleSheet() + "color: #cccccc;")
