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
from ui import get_font_families, get_bold_weight


class ComicSelectorItem(QWidget):
    """
    Custom widget for displaying individual comic strip information in the selector.
    
    This widget shows the comic's display name, author, and provides visual
    feedback for selection state.
    """
    
    def __init__(self, comic_definition: ComicDefinition, number: int = 0):
        """
        Initialize the comic selector item.

        Args:
            comic_definition: ComicDefinition object containing comic metadata
            number: Display number for the comic item (1-based)
        """
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.comic_definition = comic_definition
        self.number = number
        self.is_selected = False
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI layout and styling for the comic item."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(0)

        # Comic display name with number prefix
        name_text = f"{self.number} • {self.comic_definition.display_name}" if self.number > 0 else self.comic_definition.display_name
        self.name_label = QLabel(name_text)
        name_font = QFont()
        name_font.setFamilies(get_font_families())
        name_font.setPointSize(12)
        name_font.setWeight(get_bold_weight())
        self.name_label.setContentsMargins(0, 0, 0, 0)
        self.name_label.setFont(name_font)
        self.name_label.setStyleSheet("color: #000000; background: transparent; border: none;")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

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
                    border: none;
                }
                QLabel {
                    background: transparent;
                    border: none;
                    color: #000000;
                }
            """)
            self.name_label.setStyleSheet("color: #000000; background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                ComicSelectorItem {
                    background-color: transparent;
                    border: none;
                }
                ComicSelectorItem:hover {
                    background-color: #d0d0d0;
                    border: none;
                }
                QLabel {
                    background: transparent;
                    border: none;
                    color: #000000;
                }
            """)
            self.name_label.setStyleSheet("color: #000000; background: transparent; border: none;")
    
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
                background-color: #e8e8e8;
            }
        """)
        
        # Header section
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.NoFrame)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #e8e8e8;
                border: none;
                border-bottom: 1px solid #d0d0d0;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        
        # Title
        title_label = QLabel("Comic Strips")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setWeight(get_bold_weight())
        title_font.setFamilies(get_font_families())
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #000000; background: transparent; border: none;")
        header_layout.addWidget(title_label)        
    
        layout.addWidget(header_frame)
        
        # Scrollable comic list area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #e8e8e8;
                border: none;
            }
        """)
        
        # Container widget for comic items
        self.comics_container = QWidget()
        self.comics_container.setStyleSheet("""
            QWidget {
                background-color: #e8e8e8;
            }
        """)
        self.comics_layout = QVBoxLayout(self.comics_container)
        self.comics_layout.setContentsMargins(0, 0, 0, 0)
        self.comics_layout.setSpacing(0)
        
        self.scroll_area.setWidget(self.comics_container)
        layout.addWidget(self.scroll_area)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    
    def populate_comic_list(self):
        """Load and display all available comic strips."""
        # Clear existing items
        self.comic_items.clear()
        
        # Add each comic definition as a selectable item
        for i, comic_def in enumerate(COMIC_DEFINITIONS, start=1):
            comic_item = ComicSelectorItem(comic_def, number=i)
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
        # Validate comic name
        if not comic_name or not isinstance(comic_name, str):
            return
            
        if comic_name not in self.comic_items:
            return
        
        # Deselect previously selected comic
        if self.selected_comic and self.selected_comic in self.comic_items:
            self.comic_items[self.selected_comic].set_selected(False)
        
        # Select new comic
        self.selected_comic = comic_name
        self.comic_items[comic_name].set_selected(True)
        
        # Ensure the selected item is visible in the scroll area
        if hasattr(self, 'scroll_area') and self.scroll_area:
            self.scroll_area.ensureWidgetVisible(self.comic_items[comic_name], 0, 20)
        
        # Emit selection signal
        self.comic_selected.emit(comic_name)
    
    def select_previous_comic(self):
        """Select the previous comic in the list, cycling to the end if at the top."""
        if not COMIC_DEFINITIONS:
            return
        names = [d.name for d in COMIC_DEFINITIONS]
        try:
            current_idx = names.index(self.selected_comic)
            prev_idx = (current_idx - 1) % len(names)
        except (ValueError, TypeError):
            prev_idx = 0
        self.select_comic(names[prev_idx])

    def select_next_comic(self):
        """Select the next comic in the list, cycling to the start if at the bottom."""
        if not COMIC_DEFINITIONS:
            return
        names = [d.name for d in COMIC_DEFINITIONS]
        try:
            current_idx = names.index(self.selected_comic)
            next_idx = (current_idx + 1) % len(names)
        except (ValueError, TypeError):
            next_idx = 0
        self.select_comic(names[next_idx])
    
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
