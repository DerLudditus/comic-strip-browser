"""
Comic viewer UI component for the Comic Strip Browser application.

This module contains the ComicViewer widget which displays comic strips with
proper scaling, title information, loading states, and error handling.
"""

import os
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread, pyqtSlot
from PyQt6.QtGui import QPixmap, QFont, QPainter, QMovie
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from models.data_models import ComicData


class ImageLoader(QThread):
    """
    Background thread for loading comic images without blocking the UI.
    
    This thread handles downloading images from URLs or loading from cache,
    with proper error handling and progress reporting.
    """
    
    # Signals for communicating with the main thread
    image_loaded = pyqtSignal(QPixmap)  # Emitted when image is successfully loaded
    loading_failed = pyqtSignal(str)    # Emitted when loading fails with error message
    loading_progress = pyqtSignal(int)  # Emitted with progress percentage
    
    def __init__(self, image_source: str):
        """
        Initialize the image loader.
        
        Args:
            image_source: Either a file path (for cached images) or URL (for web images)
        """
        super().__init__()
        self.image_source = image_source
        self.network_manager = None
    
    def run(self):
        """Load the image in the background thread."""
        try:
            if self.image_source.startswith(('https://', 'http://')):
                self._load_from_url()
            else:
                self._load_from_file()
        except Exception as e:
            self.loading_failed.emit(f"Failed to load image: {str(e)}")
    
    def _load_from_file(self):
        """Load image from local file path."""
        if not os.path.exists(self.image_source):
            self.loading_failed.emit("Image file not found")
            return
        
        pixmap = QPixmap(self.image_source)
        if pixmap.isNull():
            self.loading_failed.emit("Invalid image file format")
            return
        
        self.image_loaded.emit(pixmap)
    
    def _load_from_url(self):
        """Load image from URL (simplified version - in real app would use proper networking)."""
        # For now, emit a failure since we don't have the full networking implementation
        # In the complete application, this would use QNetworkAccessManager
        self.loading_failed.emit("URL loading not implemented in this version")


class ComicViewer(QWidget):
    """
    Comic strip display widget with scaling, title display, and state management.
    
    Responsibilities:
    - Display comic images with proper scaling and aspect ratio preservation
    - Show comic titles and metadata
    - Handle loading states with progress indicators
    - Display error messages when comics are unavailable
    - Support different image formats and Sunday comic size variations
    """
    
    # Signals for UI coordination
    comic_displayed = pyqtSignal(str)  # Emitted when comic is successfully displayed
    loading_started = pyqtSignal()     # Emitted when loading begins
    loading_finished = pyqtSignal()    # Emitted when loading completes (success or failure)
    
    def __init__(self, parent=None):
        """Initialize the comic viewer widget."""
        super().__init__(parent)
        self.current_comic_data = None
        self.current_pixmap = None
        self.image_loader = None
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the main UI layout and components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header section for comic title and metadata
        self.create_header_section(layout)
        
        # Main content area with scrollable image display
        self.create_content_section(layout)
        
        # Initially show empty state
        self.show_empty_state()
    
    def create_header_section(self, parent_layout):
        """Create the header section with title and metadata display."""
        self.header_frame = QFrame()
        self.header_frame.setFrameStyle(QFrame.Shape.NoFrame)
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #e0e0e0;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(4)
        
        # Comic title
        self.title_label = QLabel("No comic selected")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #000000; font-weight: bold;")  # Ensure dark text and bold
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label)
        
        # Comic metadata (date, author, etc.)
        self.metadata_label = QLabel("")
        metadata_font = QFont()
        metadata_font.setPointSize(10)
        self.metadata_label.setFont(metadata_font)
        self.metadata_label.setStyleSheet("color: #6c757d;")
        self.metadata_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.metadata_label.setWordWrap(True)
        self.metadata_label.setVisible(False)  # Hide when empty
        header_layout.addWidget(self.metadata_label)
        
        parent_layout.addWidget(self.header_frame)
    
    def create_content_section(self, parent_layout):
        """Create the main content area with scrollable image display."""
        # Scrollable area for comic image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        # No background color set - use system theme
        
        # Content widget that will contain the comic image or state displays
        self.content_widget = QWidget()
        # No background color set - use system theme
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Comic image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(QSize(400, 300))
        self.image_label.setStyleSheet("""
            QLabel {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #fafafa;
            }
        """)
        self.content_layout.addWidget(self.image_label)
        
        # Navigation buttons under the comic
        nav_layout = QHBoxLayout()
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.setSpacing(10)
        nav_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to prevent artifacts
        
        # First button
        self.first_button = QPushButton("First")
        self.first_button.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border: 2px solid #9e9e9e;
            }
            QPushButton:pressed {
                background-color: #bdbdbd;
                border: 2px solid #757575;
            }
        """)
        nav_layout.addWidget(self.first_button)
        
        # Previous button
        self.prev_button = QPushButton("Previous")
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border: 2px solid #9e9e9e;
            }
            QPushButton:pressed {
                background-color: #bdbdbd;
                border: 2px solid #757575;
            }
        """)
        nav_layout.addWidget(self.prev_button)
        
        # Today button
        self.today_button = QPushButton("Today")
        self.today_button.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border: 2px solid #9e9e9e;
            }
            QPushButton:pressed {
                background-color: #bdbdbd;
                border: 2px solid #757575;
            }
        """)
        nav_layout.addWidget(self.today_button)
        
        # Next button
        self.next_button = QPushButton("Next")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border: 2px solid #9e9e9e;
            }
            QPushButton:pressed {
                background-color: #bdbdbd;
                border: 2px solid #757575;
            }
        """)
        nav_layout.addWidget(self.next_button)
        
        # Random button
        self.random_button = QPushButton("Random")
        self.random_button.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border: 2px solid #9e9e9e;
            }
            QPushButton:pressed {
                background-color: #bdbdbd;
                border: 2px solid #757575;
            }
        """)
        nav_layout.addWidget(self.random_button)
        
        self.content_layout.addLayout(nav_layout)
        
        # Loading progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setMaximumHeight(0)  # Collapse when hidden to prevent artifacts
        self.progress_bar.hide()  # Explicitly hide initially
        self.content_layout.addWidget(self.progress_bar)
        
        # Error/status message area
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 12px;
                padding: 10px;
            }
        """)
        self.status_label.setVisible(False)  # Hide when empty
        self.content_layout.addWidget(self.status_label)
        
        # Retry button for error states
        self.retry_button = QPushButton("Retry")
        self.retry_button.setVisible(False)
        self.retry_button.setMaximumWidth(100)
        self.retry_button.clicked.connect(self.retry_loading)
        self.content_layout.addWidget(self.retry_button)
        
        self.scroll_area.setWidget(self.content_widget)
        parent_layout.addWidget(self.scroll_area)
    
    def display_comic(self, comic_data: ComicData):
        """
        Display a comic strip with its metadata.
        
        Args:
            comic_data: ComicData object containing comic information
        """
        self.current_comic_data = comic_data
        
        # Update header with comic information
        self.update_header(comic_data)
        
        # Start loading the comic image
        self.show_loading_state()
        self.load_comic_image(comic_data)
    
    def update_header(self, comic_data: ComicData):
        """
        Update the header section with comic metadata.
        
        Args:
            comic_data: ComicData object containing comic information
        """
        # Set title from extracted HTML title (strip GoComics suffix)
        clean_title = comic_data.title.replace(" | GoComics", "")
        self.title_label.setText(clean_title)
        
        # Set metadata information
        date_str = comic_data.date.strftime("%B %d, %Y")
        # metadata_text =  f"{date_str} • by {comic_data.author}"
        
        # Add image format and dimensions info
        if comic_data.image_width and comic_data.image_height:
            # metadata_text += f" • {comic_data.image_width}×{comic_data.image_height} {comic_data.image_format.upper()}"
            metadata_text = f" {comic_data.image_width}×{comic_data.image_height}"
        
        self.metadata_label.setText(metadata_text)
        self.metadata_label.setVisible(True)  # Show metadata when we have content
    
    def load_comic_image(self, comic_data: ComicData):
        """
        Load the comic image from cache or URL.
        
        Args:
            comic_data: ComicData object containing image information
        """
        self.loading_started.emit()
        
        # Determine image source (cached file or URL)
        image_source = comic_data.cached_image_path if comic_data.cached_image_path else comic_data.image_url
        
        # Clean up previous loader
        if self.image_loader:
            self.image_loader.quit()
            self.image_loader.wait()
        
        # Start loading in background thread
        self.image_loader = ImageLoader(image_source)
        self.image_loader.image_loaded.connect(self.on_image_loaded)
        self.image_loader.loading_failed.connect(self.on_loading_failed)
        self.image_loader.loading_progress.connect(self.on_loading_progress)
        self.image_loader.start()
    
    @pyqtSlot(QPixmap)
    def on_image_loaded(self, pixmap: QPixmap):
        """
        Handle successful image loading.
        
        Args:
            pixmap: Loaded QPixmap object
        """
        self.current_pixmap = pixmap
        self.display_image(pixmap)
        self.show_image_state()
        self.loading_finished.emit()
        
        if self.current_comic_data:
            self.comic_displayed.emit(self.current_comic_data.comic_name)
    
    @pyqtSlot(str)
    def on_loading_failed(self, error_message: str):
        """
        Handle image loading failure.
        
        Args:
            error_message: Description of the loading error
        """
        self.show_error_state(error_message)
        self.loading_finished.emit()
    
    @pyqtSlot(int)
    def on_loading_progress(self, progress: int):
        """
        Handle loading progress updates.
        
        Args:
            progress: Progress percentage (0-100)
        """
        self.progress_bar.setValue(progress)
    
    def display_image(self, pixmap: QPixmap):
        """
        Display the comic image with proper scaling and aspect ratio preservation.
        
        Args:
            pixmap: QPixmap object to display
        """
        if pixmap.isNull():
            self.show_error_state("Invalid image data")
            return        
      
        # Calculate appropriate size for display
        display_size = self.calculate_display_size(pixmap.size())        
       
        # Scale pixmap while preserving aspect ratio
        scaled_pixmap = pixmap.scaled(
            display_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Update image label
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())        
    
    def calculate_display_size(self, original_size: QSize) -> QSize:
        """
        Calculate appropriate display size for comic image.
        
        Args:
            original_size: Original size of the comic image
            
        Returns:
            QSize object with calculated display dimensions
        """
        # Get available space in the scroll area
        available_size = self.scroll_area.size()
        max_width = available_size.width() - 60  # Account for margins and scrollbars
        max_height = available_size.height() - 60
        
        # Handle Sunday comics (typically larger)
        # Sunday comics are usually wider, so we give them more space
        # WRONG LOGIC! Some comics are HIGHER on Sundays, but not necessarily wider!
        # Also, sometimes we want to be able to zoon in, so...
        # Currently, I changed the limits
        if original_size.width() > original_size.height() * 1.5:
            # Likely a Sunday comic - allow more width
            max_width = min(max_width, 1350) # was 1000
            max_height = min(max_height, 930) # was 700
        else:
            # Regular daily comic
            max_width = min(max_width, 1350) # was 800
            max_height = min(max_height, 750) # was 600
        
        # Calculate scaled size while preserving aspect ratio
        original_ratio = original_size.width() / original_size.height()
        
        if max_width / max_height > original_ratio:
            # Height is the limiting factor
            new_height = max_height
            new_width = int(new_height * original_ratio)
        else:
            # Width is the limiting factor
            new_width = max_width
            new_height = int(new_width / original_ratio)
        
        return QSize(new_width, new_height)
    
    def show_loading_state(self):
        """Display loading state with progress indicator."""
        self.image_label.clear()
        self.image_label.setText("Loading comic...")
        self.image_label.setStyleSheet("""
            QLabel {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #6c757d;
                font-size: 14px;
            }
        """)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.show()  # Explicitly show the progress bar
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText("Downloading comic image...")
        self.status_label.setVisible(True)  # Show status when we have content
        self.retry_button.setVisible(False)
    
    def show_error_state(self, error_message: str, error_type: str = "general", recovery_options: list = None):
        """
        Display error state with message and recovery options.
        
        Args:
            error_message: Error message to display
            error_type: Type of error (network, parsing, unavailable, etc.)
            recovery_options: List of recovery action labels
        """
        self.image_label.clear()
        
        # Choose appropriate icon and styling based on error type
        if error_type == "network":
            icon = "🌐"
            title = "Connection Error"
            bg_color = "#fff3cd"
            border_color = "#ffeaa7"
            text_color = "#856404"
        elif error_type == "unavailable":
            icon = "📅"
            title = "Comic Not Available"
            bg_color = "#d1ecf1"
            border_color = "#bee5eb"
            text_color = "#0c5460"
        elif error_type == "parsing":
            icon = "🔧"
            title = "Loading Issue"
            bg_color = "#f8d7da"
            border_color = "#f5c6cb"
            text_color = "#721c24"
        else:
            icon = "⚠️"
            title = "Error"
            bg_color = "#f8d7da"
            border_color = "#dc3545"
            text_color = "#721c24"
        
        self.image_label.setText(f"{icon}\n{title}")
        self.image_label.setStyleSheet(f"""
            QLabel {{
                border: 1px solid {border_color};
                border-radius: 8px;
                background-color: {bg_color};
                color: {text_color};
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        
        self.progress_bar.setVisible(False)
        self.status_label.setText(error_message)
        self.status_label.setVisible(True)  # Show status when we have error content
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: 12px;
                padding: 10px;
                background-color: {bg_color};
                border-radius: 4px;
                margin: 5px;
            }}
        """)
        
        # Show recovery options
        self._show_recovery_options(recovery_options or ["Retry"])
    
    def _show_recovery_options(self, recovery_options: list):
        """
        Show recovery option buttons.
        
        Args:
            recovery_options: List of recovery action labels
        """
        # Don't show any recovery buttons - removed as per user request
        # Just make sure the old retry button is hidden
        self.retry_button.setVisible(False)
    
    def try_yesterday(self):
        """Try loading yesterday's comic."""
        from datetime import date, timedelta
        if hasattr(self, 'error_recovery_callback'):
            yesterday = date.today() - timedelta(days=1)
            self.error_recovery_callback('try_date', yesterday)
    
    def try_different_date(self):
        """Open date selection dialog."""
        if hasattr(self, 'error_recovery_callback'):
            self.error_recovery_callback('select_date', None)
    
    def select_different_comic(self):
        """Signal to select a different comic."""
        if hasattr(self, 'error_recovery_callback'):
            self.error_recovery_callback('select_comic', None)
    
    def set_error_recovery_callback(self, callback):
        """
        Set callback function for error recovery actions.
        
        Args:
            callback: Function to call with (action, data) parameters
        """
        self.error_recovery_callback = callback
    
    def show_empty_state(self):
        """Display empty state when no comic is selected."""
        self.image_label.clear()
        
        # Create a visually appealing placeholder with emoji and text
        self.image_label.setText("""
        <html>
            <body style="text-align: center;">
                <div style="font-size: 72px; margin-bottom: 20px;">📰</div>
                <div style="font-size: 24px; font-weight: bold; color: #333333;">Welcome to Comic Strip Browser</div>
                <div style="font-size: 18px; color: #555555; margin-top: 10px;">Select a comic from the left panel to begin</div>
            </body>
        </html>
        """)
        
        self.image_label.setStyleSheet("""
            QLabel {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #f8f8f8;
                padding: 20px;
            }
        """)
        
        self.progress_bar.setVisible(False)
        self.status_label.setText("Select a comic from the left")
        self.status_label.setVisible(True)  # Show status when we have content
        self.status_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        self.retry_button.setVisible(False)
    
    def show_image_state(self):
        """Display normal image state (hide loading/error elements)."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        self.status_label.setVisible(False)  # Hide status when empty
        self.retry_button.setVisible(False)
        
        # Reset image label styling for normal display
        self.image_label.setStyleSheet("""
            QLabel {
                border: none;
                border-radius: 8px;
                background-color: white;
            }
        """)
    
    def retry_loading(self):
        """Retry loading the current comic."""
        if self.current_comic_data:
            self.load_comic_image(self.current_comic_data)
    
    def get_current_comic_data(self) -> Optional[ComicData]:
        """
        Get the currently displayed comic data.
        
        Returns:
            ComicData object if comic is loaded, None otherwise
        """
        return self.current_comic_data
    
    def clear_comic(self):
        """Clear the current comic and return to empty state."""
        self.current_comic_data = None
        self.current_pixmap = None
        
        if self.image_loader:
            self.image_loader.quit()
            self.image_loader.wait()
            self.image_loader = None
        
        self.title_label.setText("No comic selected")
        self.metadata_label.setText("")
        self.metadata_label.setVisible(False)  # Hide metadata when empty
        self.show_empty_state()
    
    def resizeEvent(self, event):
        """Handle widget resize events to adjust image scaling."""
        super().resizeEvent(event)
        
        # Re-scale current image if available
        if self.current_pixmap and not self.current_pixmap.isNull():
            self.display_image(self.current_pixmap)
