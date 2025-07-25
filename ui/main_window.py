"""
Main window UI component for the Comic Strip Browser application.

This module contains the MainWindow class which serves as the primary application
window and UI coordinator, providing the basic window structure with menu bar,
toolbar, status bar, and cross-platform compatibility.
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QMenuBar, QToolBar, QStatusBar, QApplication,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

from ui.comic_selector import ComicSelector
from ui.comic_viewer import ComicViewer
from ui.calendar_widget import CalendarWidget
from ui.comic_controller import ComicController


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
        self.setWindowTitle("Comic Strip Browser 1.0.4")
        self.setMinimumSize(QSize(1000, 700))
        self.resize(QSize(1200, 840))
        
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
        
        # Set up status bar
        self.create_status_bar()
    
    def create_ui_placeholders(self):
        """Create UI components and placeholder frames."""
        # Left panel - Comic selector
        self.comic_selector = ComicSelector()
        self.comic_selector.setMinimumWidth(250)
        self.comic_selector.setMaximumWidth(300)
        
        # Connect comic selector signals
        self.comic_selector.comic_selected.connect(self.on_comic_selected)
        
        # Center panel - Comic viewer
        self.comic_viewer = ComicViewer()
        
        # Connect comic viewer signals
        self.comic_viewer.loading_started.connect(lambda: self.update_status("Loading comic..."))
        self.comic_viewer.loading_finished.connect(lambda: self.update_status("Ready", 2000))
        self.comic_viewer.comic_displayed.connect(lambda name: self.update_status(f"Displaying {name}", 3000))
        
        # Right panel - Calendar navigation widget
        self.calendar_widget = CalendarWidget()
        self.calendar_widget.setMinimumWidth(200)
        self.calendar_widget.setMaximumWidth(250)
        
        # Connect calendar widget signals
        self.calendar_widget.date_selected.connect(self.on_date_changed)
        self.calendar_widget.month_changed.connect(self.on_month_changed)
        
        # Add panels to splitter
        self.main_splitter.addWidget(self.comic_selector)
        self.main_splitter.addWidget(self.comic_viewer)
        self.main_splitter.addWidget(self.calendar_widget)
        
        # Set initial splitter proportions
        self.main_splitter.setSizes([250, 700, 250])
    
    def create_menu_bar(self):
        """Create and configure the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu (for future UI component toggles)
        view_menu = menubar.addMenu("&View")
        
        # Placeholder actions for future components
        toggle_selector_action = QAction("Show Comic &Selector", self)
        toggle_selector_action.setCheckable(True)
        toggle_selector_action.setChecked(True)
        toggle_selector_action.setStatusTip("Toggle comic selector panel")
        view_menu.addAction(toggle_selector_action)
        
        toggle_calendar_action = QAction("Show &Calendar", self)
        toggle_calendar_action.setCheckable(True)
        toggle_calendar_action.setChecked(True)
        toggle_calendar_action.setStatusTip("Toggle calendar navigation panel")
        view_menu.addAction(toggle_calendar_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.setStatusTip("About Comic Strip Browser")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create and configure the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Navigation actions (placeholders for future functionality)
        prev_action = QAction("Previous", self)
        prev_action.setStatusTip("Go to previous comic")
        prev_action.setEnabled(False)  # Will be enabled when functionality is added
        toolbar.addAction(prev_action)
        
        next_action = QAction("Next", self)
        next_action.setStatusTip("Go to next comic")
        next_action.setEnabled(False)  # Will be enabled when functionality is added
        toolbar.addAction(next_action)
        
        toolbar.addSeparator()
        
        today_action = QAction("Today", self)
        today_action.setStatusTip("Go to today's comic")
        today_action.setEnabled(False)  # Will be enabled when functionality is added
        toolbar.addAction(today_action)
        
        # Store actions for future use
        self.prev_action = prev_action
        self.next_action = next_action
        self.today_action = today_action
    
    def create_status_bar(self):
        """Create and configure the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Show ready message
        self.status_bar.showMessage("Ready", 2000)
    
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
                border-top: 1px solid #d0d0d0;
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
        self.status_bar.showMessage(f"Selected comic: {comic_name}", 3000)
        
        # Log user action for debugging
        from services.logging_service import get_logging_service
        logging_service = get_logging_service()
        logging_service.log_user_action("comic_selected", "comic_selector", {"comic_name": comic_name})
        
        self.comic_selected.emit(comic_name)
    
    def on_date_changed(self, date):
        """
        Handle calendar date selection events.
        
        Args:
            date: Selected date object
        """
        self.status_bar.showMessage(f"Selected date: {date}", 3000)
        
        # Log user action for debugging
        from services.logging_service import get_logging_service
        logging_service = get_logging_service()
        logging_service.log_user_action("date_selected", "calendar_widget", {"selected_date": str(date)})
        
        self.date_changed.emit(date)
    
    def on_month_changed(self, month: int, year: int):
        """
        Handle calendar month/year change events.
        
        Args:
            month: New month (1-12)
            year: New year
        """
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_name = month_names[month - 1]
        self.status_bar.showMessage(f"Viewing {month_name} {year}", 2000)
    
    def show_about(self):
        """Show about dialog (placeholder for future implementation)."""
        self.status_bar.showMessage("About dialog - to be implemented", 3000)
    
    def update_status(self, message: str, timeout: int = 0):
        """
        Update the status bar message.
        
        Args:
            message: Message to display
            timeout: Timeout in milliseconds (0 for permanent)
        """
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
        self.comic_selector.comic_selected.connect(self.comic_controller.select_comic)
        self.calendar_widget.date_selected.connect(self.comic_controller.select_date)
        
        # Connect controller signals to UI components
        self.comic_controller.comic_loaded.connect(self.comic_viewer.display_comic)
        self.comic_controller.comic_loading_started.connect(self.on_comic_loading_started)
        self.comic_controller.comic_loading_finished.connect(self.on_comic_loading_finished)
        self.comic_controller.loading_error.connect(self.on_loading_error)
        self.comic_controller.available_dates_updated.connect(self.on_available_dates_updated)
        
        # Connect navigation buttons in the comic viewer
        self.comic_viewer.prev_button.clicked.connect(self.go_to_previous_day)
        self.comic_viewer.next_button.clicked.connect(self.go_to_next_day)
        self.comic_viewer.today_button.clicked.connect(self.go_to_today)
    
    def on_comic_loading_started(self, comic_name: str, comic_date):
        """
        Handle comic loading started event.
        
        Args:
            comic_name: Name of the comic being loaded
            comic_date: Date of the comic being loaded
        """
        date_str = comic_date.strftime("%B %d, %Y")
        self.update_status(f"Loading {comic_name} for {date_str}...")
        
        # Show loading state in comic viewer
        self.comic_viewer.show_loading_state()
    
    def on_comic_loading_finished(self, comic_name: str, comic_date):
        """
        Handle comic loading finished event.
        
        Args:
            comic_name: Name of the comic that finished loading
            comic_date: Date of the comic that finished loading
        """
        self.update_status("Ready", 2000)
    
    def on_loading_error(self, error_message: str, recovery_suggestions: str, error_type: str = "general"):
        """
        Handle loading error event with enhanced error recovery.
        
        Args:
            error_message: User-friendly error message
            recovery_suggestions: Suggested recovery actions
            error_type: Type of error for appropriate UI styling
        """
        self.update_status(f"Error: {error_message}")
        
        # Parse recovery suggestions into actionable options
        recovery_options = self._parse_recovery_suggestions(recovery_suggestions, error_type)
        
        # Show error in comic viewer with recovery options
        self.comic_viewer.show_error_state(error_message, error_type, recovery_options)
        
        # Set up error recovery callback
        self.comic_viewer.set_error_recovery_callback(self._handle_error_recovery)
        
        # Log the error for debugging using enhanced logging service
        from services.logging_service import get_logging_service
        logging_service = get_logging_service()
        
        # Log UI error with enhanced tracking
        current_comic = self.comic_selector.get_selected_comic() if hasattr(self, 'comic_selector') else None
        current_date = self.calendar_widget.get_selected_date() if hasattr(self, 'calendar_widget') else None
        
        user_data = {
            'current_comic': current_comic,
            'current_date': str(current_date) if current_date else None,
            'window_size': f"{self.width()}x{self.height()}",
            'selected_comic_count': len(self.comic_selector.get_available_comics()) if hasattr(self.comic_selector, 'get_available_comics') else 0
        }
        
        logging_service.log_ui_error(
            error_type=error_type,
            error_message=error_message,
            component="main_window",
            recovery_actions=recovery_options,
            user_data=user_data
        )
    
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
        # Log error recovery action
        from services.logging_service import get_logging_service
        logging_service = get_logging_service()
        logging_service.log_user_action(f"error_recovery_{action}", "main_window", {"data": str(data) if data else None})
        
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
    
    def go_to_today(self):
        """Navigate to today's comic."""
        from datetime import date
        today = date.today()
        
        # Update calendar to today's date
        self.calendar_widget.navigate_to_date(today)
        
        # Load today's comic if we have a comic selected
        current_comic = self.comic_selector.get_selected_comic()
        if current_comic:
            self.comic_controller.load_comic(current_comic, today)
    
    def go_to_previous_day(self):
        """Navigate to the previous day's comic."""
        from datetime import date, timedelta
        
        current_date = self.calendar_widget.get_selected_date()
        if not current_date:
            current_date = date.today()
        
        previous_date = current_date - timedelta(days=1)
        
        # Update calendar
        self.calendar_widget.navigate_to_date(previous_date)
        
        # Load previous day's comic if we have a comic selected
        current_comic = self.comic_selector.get_selected_comic()
        if current_comic:
            self.comic_controller.load_comic(current_comic, previous_date)
    
    def go_to_next_day(self):
        """Navigate to the next day's comic."""
        from datetime import date, timedelta
        
        current_date = self.calendar_widget.get_selected_date()
        if not current_date:
            current_date = date.today()
        
        next_date = current_date + timedelta(days=1)
        
        # Don't go beyond today
        if next_date > date.today():
            self.update_status("Cannot navigate beyond today's date", 3000)
            return
        
        # Update calendar
        self.calendar_widget.navigate_to_date(next_date)
        
        # Load next day's comic if we have a comic selected
        current_comic = self.comic_selector.get_selected_comic()
        if current_comic:
            self.comic_controller.load_comic(current_comic, next_date)
    
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
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Comic Browser")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
