"""
Main window UI component for the Comic Strip Browser application.

This module contains the MainWindow class which serves as the primary application
window and UI coordinator, providing the basic window structure with menu bar,
toolbar, status bar, and cross-platform compatibility.
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStatusBar, QApplication,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon

from ui.comic_selector import ComicSelector
from ui.comic_viewer import ComicViewer
from ui.calendar_widget import CalendarWidget
from ui.comic_controller import ComicController
from models.data_models import get_comic_definition
from version import __version__


class MainWindow(QMainWindow):
    """
    Primary application window and UI coordinator.
    
    Responsibilities:
    - Initialize and manage all UI components
    - Handle menu actions and toolbar interactions
    - Coordinate between different UI panels
    - Provide cross-platform compatibility settings
    """
    
    # Signals for UI coordination
    comic_selected = pyqtSignal(str)  # Emitted when a comic is selected
    date_changed = pyqtSignal(object)  # Emitted when calendar date changes
    
    def __init__(self):
        """Initialize the main window with basic structure."""
        super().__init__()
        self.comic_controller = None
        self.initialize_ui()
        self.setup_cross_platform_compatibility()
        self.setup_controller_integration()
    
    def initialize_ui(self):
        """Set up the main window layout and components."""
        # Set window properties
        self.setWindowTitle(f"Comic Strip Browser {__version__}")
        self.setMinimumSize(QSize(1000, 700))
        self.resize(QSize(1200, 840))

        # Set up status bar FIRST
        self.create_status_bar()

 
        
        # Set application icon to comicicon.png
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "comicicon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon())  # Fallback if icon doesn't exist
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout using splitter for resizable panels
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create horizontal splitter for main content areas
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Create placeholder frames for future UI components
        self.create_ui_placeholders()
    
    def create_ui_placeholders(self):
        """Create UI components and placeholder frames."""
        # Left panel - Comic selector
        self.comic_selector = ComicSelector()
        self.comic_selector.setMinimumWidth(250)
        self.comic_selector.setMaximumWidth(350)
        
        # Connect comic selector signals
        self.comic_selector.comic_selected.connect(self.on_comic_selected)
        
        # Center panel - Comic viewer
        self.comic_viewer = ComicViewer()
        
        # Connect comic viewer signals
        self.comic_viewer.loading_started.connect(lambda: self.update_status("Loading comic..."))
        self.comic_viewer.loading_finished.connect(lambda: self.update_status("Ready", 2000))
        self.comic_viewer.comic_displayed.connect(self.on_comic_displayed)
        
        # Right panel - Calendar navigation widget
        self.calendar_widget = CalendarWidget()
        self.calendar_widget.setMinimumWidth(250)
        self.calendar_widget.setMaximumWidth(350)
        
        # Connect calendar widget signals
        self.calendar_widget.date_selected.connect(self.on_date_changed)
        self.calendar_widget.month_changed.connect(self.on_month_changed)
        
        # Add panels to splitter
        self.main_splitter.addWidget(self.comic_selector)
        self.main_splitter.addWidget(self.comic_viewer)
        self.main_splitter.addWidget(self.calendar_widget)
        
        # Set initial splitter proportions
        self.main_splitter.setSizes([250, 700, 250])
    

    

    
    def create_status_bar(self):
        """Create and configure the status bar."""
        self.status_bar = QStatusBar()
        self.status_bar.setVisible(True)
        self.status_bar.setSizeGripEnabled(True)
        
        # Set minimum height to ensure visibility
        self.status_bar.setMinimumHeight(25)
        
        # Set status bar with explicit styling
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #d0d0d0;
                color: #333333;
                font-size: 14px;
                padding: 2px;
            }
        """)
        
        self.setStatusBar(self.status_bar)
        
        # Show ready message with version after a short delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.status_bar.showMessage(f"Ready - v{__version__}", 0))
    
    def setup_cross_platform_compatibility(self):
        """Configure settings for cross-platform compatibility."""
        # Set consistent style across platforms
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QFrame {
                background-color: white;
                border: 1px solid #d0d0d0;
            }
            QToolBar {
                border: none;
                spacing: 3px;
            }
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #d0d0d0;
                color: #333333;
                font-size: 14px;
                min-height: 25px;
                padding: 2px;
            }
        """)
        
        # Platform-specific adjustments
        if sys.platform == "win32":
            # Windows-specific settings
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        elif sys.platform == "linux":
            # Linux-specific settings
            pass  # Default settings work well on Linux
    
    def on_comic_selected(self, comic_name: str):
        """
        Handle comic selection events.
        
        Args:
            comic_name: Name of the selected comic strip
        """
        from datetime import date, timedelta
        
        # Guard against invalid comic names
        if not comic_name or not isinstance(comic_name, str) or len(comic_name) == 0:
            self.update_status("Invalid comic selection", 3000)
            return
        
        self.status_bar.showMessage(f"Selected comic: {comic_name}", 3000)
        
        current_date = self.calendar_widget.get_selected_date()
        comic_def = get_comic_definition(comic_name)
        today = date.today()
        
        # Determine target date: prefer today, but respect comic's date range
        if not current_date:
            # No date selected - start with today (or yesterday if today not available)
            target_date = today
        else:
            # Date already selected - only change if it's before comic's start date
            if comic_def and comic_def.earliest_date and current_date < comic_def.earliest_date:
                # Current date is before comic start - use comic's start date
                target_date = comic_def.earliest_date
            else:
                # Current date is valid for this comic - keep it
                target_date = current_date
        
        # Navigate to target date and load comic (don't emit signal to prevent double-load)
        self.calendar_widget.navigate_to_date(target_date, emit_signal=False)
        self.comic_controller.load_comic(comic_name, target_date)
        
        self.comic_selected.emit(comic_name)
    
    def on_date_changed(self, date):
        """
        Handle calendar date selection events.
        
        Args:
            date: Selected date object
        """
        self.status_bar.showMessage(f"Selected date: {date}", 3000)
        
        # Load comic for the selected date
        current_comic = self.comic_selector.get_selected_comic()
        
        # Guard against invalid comic names
        if not current_comic or not isinstance(current_comic, str) or len(current_comic) == 0:
            self.update_status("Please select a comic from the list", 3000)
            return
        
        # Additional validation - check if comic exists in definitions
        from models.data_models import get_comic_definition
        if not get_comic_definition(current_comic):
            self.update_status(f"Invalid comic selection: {current_comic}", 3000)
            return
        
        self.comic_controller.load_comic(current_comic, date)
        self.date_changed.emit(date)
    
    def on_month_changed(self, month: int, year: int):
        """
        Handle calendar month/year change events.
        
        Args:
            month: New month (1-12)
            year: New year
        """
        month_names = [
            "Jan.", "Feb.", "March", "April", "May", "June",
            "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."
        ]
        month_name = month_names[month - 1]
        self.status_bar.showMessage(f"Viewing {month_name} {year}", 2000)
    
    def on_comic_displayed(self, comic_name: str):
        """
        Handle comic displayed event and show start date info.
        
        Args:
            comic_name: Name of the displayed comic
        """
        comic_def = get_comic_definition(comic_name)
        if comic_def and comic_def.earliest_date:
            start_date_str = comic_def.earliest_date.strftime("%B %d, %Y")
            message = f"{comic_def.display_name} on GoComics.com starts on {start_date_str}"
            self.update_status(message, 0)  # Permanent message (timeout = 0)
        else:
            # Fallback if no start date found
            self.update_status(f"Displaying {comic_name}", 0)
    

    
    def update_status(self, message: str, timeout: int = 0):
        """
        Update the status bar message.
        
        Args:
            message: Message to display
            timeout: Timeout in milliseconds (0 for permanent)
        """
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.showMessage(message, timeout)
    
    def get_comic_selector(self) -> ComicSelector:
        """Get the comic selector widget."""
        return self.comic_selector
    
    def get_comic_viewer(self) -> ComicViewer:
        """Get the comic viewer widget."""
        return self.comic_viewer
    
    def get_calendar_widget(self) -> CalendarWidget:
        """Get the calendar widget."""
        return self.calendar_widget
    
    def setup_controller_integration(self):
        """Set up the comic controller and integrate it with UI components."""
        # Create the comic controller
        self.comic_controller = ComicController()
        
        # Connect UI components to controller
        # NOTE: Don't connect these to controller - we handle them in on_comic_selected and on_date_changed
        # self.comic_selector.comic_selected.connect(self.comic_controller.select_comic)
        # self.calendar_widget.date_selected.connect(self.comic_controller.select_date)
        
        # Connect controller signals to UI components
        self.comic_controller.comic_loaded.connect(self.comic_viewer.display_comic)
        self.comic_controller.comic_loading_started.connect(self.on_comic_loading_started)
        self.comic_controller.comic_loading_finished.connect(self.on_comic_loading_finished)
        self.comic_controller.loading_error.connect(self.on_loading_error)
        self.comic_controller.available_dates_updated.connect(self.on_available_dates_updated)
        
        # Add debounce tracking
        self._last_error_time = 0
        self._last_error_message = ""
        

        
        # Connect navigation buttons in the comic viewer
        if hasattr(self.comic_viewer, 'first_button'):
            self.comic_viewer.first_button.clicked.connect(self.go_to_first)
        
        if hasattr(self.comic_viewer, 'prev_button'):
            self.comic_viewer.prev_button.clicked.connect(self.go_to_previous_day)
        
        if hasattr(self.comic_viewer, 'next_button'):
            self.comic_viewer.next_button.clicked.connect(self.go_to_next_day)
        
        if hasattr(self.comic_viewer, 'today_button'):
            self.comic_viewer.today_button.clicked.connect(self.go_to_today)
        
        if hasattr(self.comic_viewer, 'random_button'):
            self.comic_viewer.random_button.clicked.connect(self.go_to_random)
        
        # Add keyboard shortcuts for navigation
        from PyQt6.QtGui import QShortcut, QKeySequence
        from PyQt6.QtCore import Qt
        
        # Left arrow = Previous
        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.shortcut_prev.activated.connect(self.go_to_previous_day)
        
        # Right arrow = Next
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.shortcut_next.activated.connect(self.go_to_next_day)
        
        # Home = First
        self.shortcut_first = QShortcut(QKeySequence(Qt.Key.Key_Home), self)
        self.shortcut_first.activated.connect(self.go_to_first)
        
        # End = Today
        self.shortcut_today = QShortcut(QKeySequence(Qt.Key.Key_End), self)
        self.shortcut_today.activated.connect(self.go_to_today)
    
    def on_comic_loading_started(self, comic_name: str, comic_date):
        """
        Handle comic loading started event.
        
        Args:
            comic_name: Name of the comic being loaded
            comic_date: Date of the comic being loaded
        """
        date_str = comic_date.strftime("%B %d, %Y")
        self.update_status(f"Loading {comic_name} for {date_str}...")
        
        # Clear any previous error messages
        self._last_error_message = ""
        
        # Show loading state in comic viewer (this clears errors)
        self.comic_viewer.show_loading_state()
    
    def on_comic_loading_finished(self, comic_name: str, comic_date):
        """
        Handle comic loading finished event.
        
        Args:
            comic_name: Name of the comic that finished loading
            comic_date: Date of the comic that finished loading
        """
        # Stop auto-advancing when we successfully load a comic
        if hasattr(self, '_auto_advancing'):
            self._auto_advancing = False
        
        self.update_status("Ready", 2000)
    
    def on_loading_error(self, error_message: str, recovery_suggestions: str, error_type: str = "general"):
        """
        Handle loading error event with enhanced error recovery.
        
        Args:
            error_message: User-friendly error message
            recovery_suggestions: Suggested recovery actions
            error_type: Type of error for appropriate UI styling
        """
        # Debounce multiple error signals for the same error
        import time
        current_time = time.time()
        
        # Ignore duplicate errors within 2 seconds
        if (current_time - self._last_error_time < 2.0 and 
            error_message == self._last_error_message):
            return
        
        self._last_error_time = current_time
        self._last_error_message = error_message
        
        # If we're in auto-advance mode, keep trying the next day
        if hasattr(self, '_auto_advancing') and self._auto_advancing:
            from datetime import date, timedelta
            
            current_date = self.calendar_widget.get_selected_date()
            start_date = self._auto_advance_start
            
            # Check if we've searched too far (31 days)
            days_searched = (current_date - start_date).days
            if days_searched >= 31:
                self._auto_advancing = False
                self.update_status(f"No comics found in next 31 days", 3000)
                return
            
            # Try the next day automatically
            next_date = current_date + timedelta(days=1)
            today = date.today()
            
            if next_date > today:
                self._auto_advancing = False
                self.update_status("Reached today's date - no more comics available", 3000)
                return
            
            # Show progress
            comic_def = get_comic_definition(self._auto_advance_comic)
            comic_display_name = comic_def.display_name if comic_def else self._auto_advance_comic
            self.update_status(f"Searching for next {comic_display_name}... {next_date.strftime('%b %d')}")
            
            # Keep trying
            self.calendar_widget.navigate_to_date(next_date)
            self.comic_controller.load_comic(self._auto_advance_comic, next_date)
            return
        
        # Not in auto-advance mode - show the error normally
        self.update_status(f"Error: {error_message}")
        
        # Parse recovery suggestions into actionable options
        recovery_options = self._parse_recovery_suggestions(recovery_suggestions, error_type)
        
        # Show error in comic viewer with recovery options
        self.comic_viewer.show_error_state(error_message, error_type, recovery_options)
        
        # Set up error recovery callback
        self.comic_viewer.set_error_recovery_callback(self._handle_error_recovery)
    

        

    
    def _parse_recovery_suggestions(self, suggestions: str, error_type: str) -> list:
        """
        Parse recovery suggestions into UI action buttons.
        
        Args:
            suggestions: Semicolon-separated recovery suggestions
            error_type: Type of error to determine appropriate actions
            
        Returns:
            List of recovery action labels
        """
        recovery_options = ["Retry"]  # Always include retry
        
        if error_type == "network":
            recovery_options.extend(["Try Yesterday", "Try Different Date"])
        elif error_type == "unavailable":
            recovery_options.extend(["Try Yesterday", "Try Different Date", "Select Different Comic"])
        elif error_type == "parsing":
            recovery_options.extend(["Try Different Date", "Select Different Comic"])
        
        # Parse specific suggestions from the error handler
        if suggestions:
            suggestion_list = [s.strip().lower() for s in suggestions.split(';')]
            
            if any("previous day" in s or "yesterday" in s for s in suggestion_list):
                if "Try Yesterday" not in recovery_options:
                    recovery_options.append("Try Yesterday")
            
            if any("different date" in s for s in suggestion_list):
                if "Try Different Date" not in recovery_options:
                    recovery_options.append("Try Different Date")
            
            if any("different comic" in s or "another comic" in s for s in suggestion_list):
                if "Select Different Comic" not in recovery_options:
                    recovery_options.append("Select Different Comic")
        
        return recovery_options
    
    def _handle_error_recovery(self, action: str, data):
        """
        Handle error recovery actions from the comic viewer.
        
        Args:
            action: Recovery action to perform
            data: Additional data for the action
        """

        
        if action == "try_date":
            # Load comic for specific date
            current_comic = self.comic_selector.get_selected_comic()
            if current_comic and data:
                self.calendar_widget.navigate_to_date(data)
                self.comic_controller.load_comic(current_comic, data)
                self.update_status(f"Trying {data.strftime('%B %d, %Y')}...")
        
        elif action == "select_date":
            # Open calendar for date selection
            self._show_date_selection_dialog()
        
        elif action == "select_comic":
            # Focus on comic selector
            self.comic_selector.setFocus()
            self.update_status("Please select a different comic from the list")
            
            # Optionally show a tooltip or highlight the comic selector
            self._highlight_comic_selector()
    
    def _show_date_selection_dialog(self):
        """Show a date selection dialog for error recovery."""
        from PyQt6.QtWidgets import QCalendarWidget, QDialog, QVBoxLayout, QPushButton, QHBoxLayout
        from datetime import date
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Date")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Calendar widget
        calendar = QCalendarWidget()
        calendar.setMaximumDate(date.today())
        
        # Set available dates if we have a current comic
        current_comic = self.comic_selector.get_selected_comic()
        if current_comic:
            available_dates = self.comic_controller.get_available_dates(current_comic)
            # Note: QCalendarWidget doesn't have a direct way to highlight specific dates
            # In a full implementation, we'd customize the calendar widget
        
        layout.addWidget(calendar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("Load Comic")
        ok_button.clicked.connect(lambda: self._load_selected_date(calendar.selectedDate().toPython(), dialog))
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _load_selected_date(self, selected_date, dialog):
        """Load comic for the selected date from the dialog."""
        current_comic = self.comic_selector.get_selected_comic()
        if current_comic:
            self.calendar_widget.navigate_to_date(selected_date)
            self.comic_controller.load_comic(current_comic, selected_date)
            self.update_status(f"Loading {current_comic} for {selected_date.strftime('%B %d, %Y')}...")
        
        dialog.accept()
    
    def _highlight_comic_selector(self):
        """Temporarily highlight the comic selector to draw attention."""
        from PyQt6.QtCore import QTimer
        
        # Add temporary highlighting style
        original_style = self.comic_selector.styleSheet()
        highlight_style = original_style + """
            QWidget {
                border: 2px solid #007bff;
                border-radius: 4px;
            }
        """
        
        self.comic_selector.setStyleSheet(highlight_style)
        
        # Remove highlighting after 3 seconds
        def remove_highlight():
            self.comic_selector.setStyleSheet(original_style)
        
        QTimer.singleShot(3000, remove_highlight)
    
    def on_available_dates_updated(self, comic_name: str, available_dates):
        """
        Handle available dates update event.
        
        Args:
            comic_name: Name of the comic
            available_dates: Set of available dates for the comic
        """
        # Update calendar widget with available dates if this is the current comic
        current_comic = self.comic_selector.get_selected_comic()
        if current_comic == comic_name:
            self.calendar_widget.set_available_dates(available_dates)
    
    def go_to_first(self):
        """Navigate to the first available comic (start date)."""
        current_comic = self.comic_selector.get_selected_comic()
        if current_comic:
            comic_def = get_comic_definition(current_comic)
            if comic_def and comic_def.earliest_date:
                # Update calendar to the start date (don't emit signal to prevent double-load)
                self.calendar_widget.navigate_to_date(comic_def.earliest_date, emit_signal=False)
                
                # Load the first comic
                self.comic_controller.load_comic(current_comic, comic_def.earliest_date)
            else:
                self.update_status("No start date available for this comic", 3000)
        else:
            self.update_status("Please select a comic first", 3000)
    
    def go_to_today(self):
        """Navigate to today's comic, or yesterday if today not available."""
        from datetime import date
        
        today = date.today()
        
        current_comic = self.comic_selector.get_selected_comic()
        if not current_comic:
            self.update_status("Please select a comic first", 3000)
            return
        
        # Update calendar to today's date (don't emit signal to prevent double-load)
        self.calendar_widget.navigate_to_date(today, emit_signal=False)
        
        # Try to load today's comic (let the error handler deal with failures)
        self.comic_controller.load_comic(current_comic, today)
    
    def go_to_previous_day(self):
        """Navigate to the previous day's comic - synchronous search."""
        from datetime import date, timedelta
        from PyQt6.QtWidgets import QApplication
        
        current_date = self.calendar_widget.get_selected_date()
        if not current_date:
            self.update_status("Please select a date first", 3000)
            return
        
        current_comic = self.comic_selector.get_selected_comic()
        if not current_comic:
            self.update_status("Please select a comic first", 3000)
            return
        
        comic_def = get_comic_definition(current_comic)
        comic_display_name = comic_def.display_name if comic_def else current_comic
        earliest_date = comic_def.earliest_date if comic_def else date(1900, 1, 1)
        
        # Search synchronously for up to 31 days backward
        for day_offset in range(1, 32):
            search_date = current_date - timedelta(days=day_offset)
            
            # Don't go before comic start
            if search_date < earliest_date:
                self.update_status("Reached comic's start date", 3000)
                return
            
            # Show progress
            self.update_status(f"Trying {comic_display_name} for {search_date.strftime('%b %d')}...")
            QApplication.processEvents()
            
            # Try to fetch this comic using the existing service
            try:
                comic_service = self.comic_controller.comic_service
                
                # Quick check: is it in cache?
                cached = comic_service.cache_manager.get_cached_comic(current_comic, search_date)
                if cached:
                    self.calendar_widget.navigate_to_date(search_date, emit_signal=False)
                    self.comic_viewer.display_comic(cached)
                    self.update_status("Ready", 2000)
                    return
                
                # Not cached - use the comic service to fetch it
                comic_data = comic_service.get_comic(current_comic, search_date)
                
                # Success! Navigate and display
                self.calendar_widget.navigate_to_date(search_date, emit_signal=False)
                self.comic_viewer.display_comic(comic_data)
                self.update_status("Ready", 2000)
                return
                
            except Exception as e:
                # Comic doesn't exist for this date, continue to previous
                error_str = str(e).lower()
                if 'not available' in error_str:
                    continue
                else:
                    continue
        
        self.update_status(f"No {comic_display_name} found in previous 31 days", 3000)
    
    def go_to_next_day(self):
        """Navigate to the next day's comic - synchronous search."""
        from datetime import date, timedelta
        from PyQt6.QtWidgets import QApplication
        
        current_date = self.calendar_widget.get_selected_date()
        if not current_date:
            self.update_status("Please select a date first", 3000)
            return
        
        current_comic = self.comic_selector.get_selected_comic()
        if not current_comic:
            self.update_status("Please select a comic first", 3000)
            return
        
        comic_def = get_comic_definition(current_comic)
        comic_display_name = comic_def.display_name if comic_def else current_comic
        today = date.today()
        
        # Search synchronously for up to 31 days
        for day_offset in range(1, 32):
            search_date = current_date + timedelta(days=day_offset)
            
            # Don't go beyond today
            if search_date > today:
                self.update_status("Reached today's date", 3000)
                return
            
            # Show progress
            self.update_status(f"Trying {comic_display_name} for {search_date.strftime('%b %d')}...")
            QApplication.processEvents()  # Keep UI responsive
            
            # Try to fetch this comic using the existing service (but catch errors quickly)
            try:
                comic_service = self.comic_controller.comic_service
                
                # Quick check: is it in cache?
                cached = comic_service.cache_manager.get_cached_comic(current_comic, search_date)
                if cached:
                    self.calendar_widget.navigate_to_date(search_date, emit_signal=False)
                    self.comic_viewer.display_comic(cached)
                    self.update_status("Ready", 2000)
                    return
                
                # Not cached - use the comic service to fetch it
                # This will use proper headers, cookies, etc.
                comic_data = comic_service.get_comic(current_comic, search_date)
                
                # Success! Navigate and display
                self.calendar_widget.navigate_to_date(search_date, emit_signal=False)
                self.comic_viewer.display_comic(comic_data)
                self.update_status("Ready", 2000)
                return
                
            except Exception as e:
                # Comic doesn't exist for this date, continue to next
                error_str = str(e).lower()
                if 'not available' in error_str:
                    # Fast fail - comic doesn't exist
                    continue
                else:
                    # Other error - continue
                    continue
        
        self.update_status(f"No {comic_display_name} found in next 31 days", 3000)
    
    def go_to_random(self):
        """Navigate to a random date's comic for the currently selected comic."""
        import random
        from datetime import date, timedelta
        from PyQt6.QtWidgets import QApplication
        
        current_comic = self.comic_selector.get_selected_comic()
        if not current_comic:
            self.update_status("Please select a comic first", 3000)
            return
        
        comic_def = get_comic_definition(current_comic)
        comic_display_name = comic_def.display_name if comic_def else current_comic
        earliest_date = comic_def.earliest_date if comic_def else date(2000, 1, 1)
        today = date.today()
        
        # Calculate the date range
        days_available = (today - earliest_date).days
        if days_available < 0:
            self.update_status("No comics available yet for this title", 3000)
            return
        
        # Pick ONE random date
        random_offset = random.randint(0, days_available)
        random_date = earliest_date + timedelta(days=random_offset)
        
        # Now iterate forward from that date until we find a comic (max 31 days)
        for day_offset in range(31):
            search_date = random_date + timedelta(days=day_offset)
            
            # Don't go beyond today
            if search_date > today:
                self.update_status("Reached today's date", 3000)
                return
            
            # Show progress
            self.update_status(f"Trying {comic_display_name} for {search_date.strftime('%b %d, %Y')}...")
            QApplication.processEvents()
            
            # Try to fetch this comic
            try:
                comic_service = self.comic_controller.comic_service
                
                # Quick check: is it in cache?
                cached = comic_service.cache_manager.get_cached_comic(current_comic, search_date)
                if cached:
                    self.calendar_widget.navigate_to_date(search_date, emit_signal=False)
                    self.comic_viewer.display_comic(cached)
                    self.update_status("Ready", 2000)
                    return
                
                # Not cached - fetch it
                comic_data = comic_service.get_comic(current_comic, search_date)
                
                # Success! Navigate and display
                self.calendar_widget.navigate_to_date(search_date, emit_signal=False)
                self.comic_viewer.display_comic(comic_data)
                self.update_status("Ready", 2000)
                return
                
            except Exception as e:
                # Comic doesn't exist for this date, continue to next day
                continue
        
        self.update_status(f"No {comic_display_name} found in 31 days from random date", 3000)

    
    def get_comic_controller(self) -> ComicController:
        """Get the comic controller instance."""
        return self.comic_controller
    
    def closeEvent(self, event):
        """Handle application close event."""
        self.update_status("Closing application...")
        
        # Clean up controller resources
        if self.comic_controller:
            self.comic_controller.cleanup()
        
        event.accept()


def main():
    """Main function for testing the MainWindow independently."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Comic Strip Browser")
    app.setApplicationVersion("1.0.5")
    app.setOrganizationName("Comic Browser")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
