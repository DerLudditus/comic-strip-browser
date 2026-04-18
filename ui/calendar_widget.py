"""
Calendar navigation widget for the Comic Strip Browser application.

This module contains the CalendarWidget which provides month/year navigation controls,
date selection handling, visual indicators for available comic dates, and date
validation against comic availability ranges.
"""

from datetime import date, datetime, timedelta
from typing import Set, Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QButtonGroup, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDate
from PyQt6.QtGui import QFont, QPalette, QColor

from models.data_models import ComicDefinition, get_comic_definition

INFO_ICON = "\U0001F4A1"

class CalendarDayButton(QPushButton):
    """
    Custom button for calendar days with availability indicators.
    
    This button represents a single day in the calendar and can show
    different states: available, unavailable, selected, and today.
    """
    
    def __init__(self, day: int, date_obj: date):
        """
        Initialize the calendar day button.
        
        Args:
            day: Day number (1-31)
            date_obj: The actual date this button represents
        """
        super().__init__(str(day))
        self.day = day
        self.date_obj = date_obj
        self.is_available = False
        self.is_selected = False
        self.is_today = False
        
        self.setFixedSize(QSize(35, 35))
        self.setCheckable(True)
        self.update_style()
    
    def set_available(self, available: bool):
        """
        Set whether this date has available comic content.
        
        Args:
            available: True if comic is available for this date
        """
        self.is_available = available
        self.update_style()
    
    def set_selected(self, selected: bool):
        """
        Set the selection state of this day.
        
        Args:
            selected: True if this day is selected
        """
        self.is_selected = selected
        self.setChecked(selected)
        self.update_style()
    
    def set_today(self, is_today: bool):
        """
        Set whether this day represents today's date.
        
        Args:
            is_today: True if this is today's date
        """
        self.is_today = is_today
        self.update_style()
    
    def update_style(self):
        """Update the button styling based on current state."""
        if self.is_selected:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2196f3;
                    color: white;
                    border: 2px solid #1976d2;
                    border-radius: 17px;
                }
                QPushButton:hover {
                    background-color: #1976d2;
                }
            """)
            self.setEnabled(True)
        elif not self.is_available:
            # Future date or before comic start — gray, not clickable
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    color: #c0c0c0;
                    border: 1px solid #e0e0e0;
                    border-radius: 17px;
                }
            """)
            self.setEnabled(False)
        elif self.is_today:
            # Today — orange outline, clickable
            self.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #333333;
                    border: 2px solid #ff9800;
                    border-radius: 17px;
                }
                QPushButton:hover {
                    background-color: #fff3e0;
                }
            """)
            self.setEnabled(True)
        else:
            # Normal available date
            self.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #e0e0e0;
                    border-radius: 17px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border: 1px solid #bdbdbd;
                }
                QPushButton:checked {
                    background-color: #2196f3;
                    color: white;
                    border: 2px solid #1976d2;
                }
            """)
            self.setEnabled(True)

class CalendarWidget(QWidget):
    """
    Calendar navigation widget with month/year controls and date selection.
    
    Responsibilities:
    - Display a calendar widget showing one month at a time
    - Provide easy controls to change months and years
    - Handle date selection and emit events
    - Show visual indicators for available comic dates
    - Validate dates against comic availability ranges
    """
    
    # Signals for date navigation
    date_selected = pyqtSignal(date)  # Emitted when a date is selected
    month_changed = pyqtSignal(int, int)  # Emitted when month/year changes (month, year)
    
    def __init__(self, parent=None):
        """Initialize the calendar widget."""
        super().__init__(parent)
        
        # Current calendar state
        self.current_date = date.today().replace(day=1)
        self.selected_date = None
        self.available_dates: Set[date] = set()
        self.comic_date_ranges: Dict[str, tuple] = {}  # Maps comic name to (start_date, end_date)
        self.current_comic_name: Optional[str] = None  # Track selected comic for date constraints
        
        # UI components
        self.day_buttons: Dict[date, CalendarDayButton] = {}
        self.day_button_group = QButtonGroup()
        self.day_button_group.setExclusive(True)
        
        self.setup_ui()
        self.populate_calendar()
    
    def setup_ui(self):
        """Set up the main UI layout and components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header section
        self.create_header_section(layout)

        # Day of week headers (outside calendar frame to sit higher)
        self.create_day_headers(layout)

        # Calendar grid section
        self.create_calendar_section(layout)

        # Info text section
        self.create_info_section(layout)

        # Push everything to the top
        layout.addStretch(1)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(290)
    
    def create_header_section(self, parent_layout):
        """Create navigation controls with month on top, year buttons below."""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        header_layout.setContentsMargins(4, 4, 4, 4)

        # Row 1: Previous month | Month Year | Next month
        month_nav_layout = QHBoxLayout()
        month_nav_layout.setSpacing(4)
        month_nav_layout.setContentsMargins(4, 2, 4, 2)

        # Previous month button — larger, prominent
        self.prev_month_btn = QPushButton("‹")
        self.prev_month_btn.setFixedSize(QSize(36, 32))
        self.prev_month_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 2px solid #bdbdbd;
                border-radius: 14px;
                font-size: 20px;
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
        self.prev_month_btn.clicked.connect(self.go_to_previous_month)
        month_nav_layout.addWidget(self.prev_month_btn)

        # Month/Year display — center, prominent
        self.month_year_label = QLabel()
        month_year_font = QFont()
        month_year_font.setPointSize(13)
        month_year_font.setBold(True)
        self.month_year_label.setFont(month_year_font)
        self.month_year_label.setStyleSheet("color: #000000;")
        self.month_year_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        month_nav_layout.addWidget(self.month_year_label, 1)

        # Next month button — larger, prominent
        self.next_month_btn = QPushButton("›")
        self.next_month_btn.setFixedSize(QSize(36, 32))
        self.next_month_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 2px solid #bdbdbd;
                border-radius: 14px;
                font-size: 20px;
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
        self.next_month_btn.clicked.connect(self.go_to_next_month)
        month_nav_layout.addWidget(self.next_month_btn)

        header_layout.addLayout(month_nav_layout)

        # Row 2: Previous year | spacer | Next year
        year_nav_layout = QHBoxLayout()
        year_nav_layout.setSpacing(4)
        year_nav_layout.setContentsMargins(4, 0, 4, 2)

        # Previous year button — shows the year it would navigate to
        self.prev_year_btn = QPushButton()
        self.prev_year_btn.setFixedHeight(32)
        self.prev_year_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #bdbdbd;
                border-radius: 4px;
                font-size: 16px;
                padding: 0px 8px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border: 1px solid #9e9e9e;
            }
            QPushButton:pressed {
                background-color: #bdbdbd;
                border: 1px solid #757575;
            }
            QPushButton:disabled {
                color: #aaaaaa;
            }
        """)
        self.prev_year_btn.clicked.connect(self.go_to_previous_year)
        year_nav_layout.addWidget(self.prev_year_btn)

        # Spacer
        year_nav_layout.addStretch(1)

        # Next year button — shows the year it would navigate to
        self.next_year_btn = QPushButton()
        self.next_year_btn.setFixedHeight(32)
        self.next_year_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #bdbdbd;
                border-radius: 4px;
                font-size: 16px;
                padding: 0px 8px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border: 1px solid #9e9e9e;
            }
            QPushButton:pressed {
                background-color: #bdbdbd;
                border: 1px solid #757575;
            }
            QPushButton:disabled {
                color: #aaaaaa;
            }
        """)
        self.next_year_btn.clicked.connect(self.go_to_next_year)
        year_nav_layout.addWidget(self.next_year_btn)

        header_layout.addLayout(year_nav_layout)

        parent_layout.addLayout(header_layout)
    
    def create_calendar_section(self, parent_layout):
        """Create the calendar grid section."""
        calendar_frame = QFrame()
        calendar_frame.setFrameStyle(QFrame.Shape.NoFrame)
        calendar_frame.setStyleSheet("""
            QFrame {
                background-color: #e0e0e0;
                border: 1px solid #c0c0c0;
            }
        """)

        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(12, 0, 12, 12)  # Zero top margin
        calendar_layout.setSpacing(0)

        # Calendar grid
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(3)
        calendar_layout.addLayout(self.calendar_grid)

        parent_layout.addWidget(calendar_frame)
    
    def create_day_headers(self, parent_layout):
        """Create the day of week header labels."""
        headers_layout = QHBoxLayout()
        headers_layout.setSpacing(2)
        
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        
        for day_name in day_names:
            header_label = QLabel(day_name)
            header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_label.setFixedSize(QSize(35, 25))
            header_font = QFont()
            header_font.setPointSize(10)
            header_font.setBold(True)
            header_label.setFont(header_font)
            header_label.setStyleSheet("""
                QLabel {
                    color: #000000;
                    background-color: #e0e0e0;
                    border-radius: 4px;
                }
            """)
            headers_layout.addWidget(header_label)
        
        parent_layout.addLayout(headers_layout)

    def create_info_section(self, parent_layout):
        """Create info text area below the calendar."""
        self.info_label = QLabel("")
        info_font = QFont()
        info_font.setPointSize(13)
        info_font.setFamilies(["Noto Sans", "Segoe UI", "Arial", "sans-serif"])
        self.info_label.setFont(info_font)
        self.info_label.setStyleSheet("""
            QLabel {
                color: #000000;
                background-color: #f0f0f0;
                padding: 6px 12px;
            }
        """)
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setMinimumHeight(30)
        parent_layout.addWidget(self.info_label)

    def set_comic_info(self, comic_name: str):
        """Update the info text and date constraints for the currently selected comic."""
        self.current_comic_name = comic_name
        comic_def = get_comic_definition(comic_name)
        if comic_def and comic_def.info:
            self.info_label.setText(INFO_ICON + " " + comic_def.info)
        else:
            self.info_label.setText("")

    def populate_calendar(self):
        """Populate the calendar grid with day buttons for the current month."""
        # Clear existing buttons
        self.clear_calendar_grid()
        
        # Get first day of the month and number of days
        first_day = date(self.current_date.year, self.current_date.month, 1)
        
        # Calculate the number of days in the month
        if self.current_date.month == 12:
            next_month = date(self.current_date.year + 1, 1, 1)
        else:
            next_month = date(self.current_date.year, self.current_date.month + 1, 1)
        
        days_in_month = (next_month - first_day).days
        
        # Get the day of week for the first day (0 = Monday, 6 = Sunday)
        # Convert to calendar format (0 = Sunday, 6 = Saturday)
        first_weekday = (first_day.weekday() + 1) % 7
        
        # Update month/year label
        month_names = [
            "Jan.", "Feb.", "March", "April", "May", "June",
            "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."
        ]
        self.month_year_label.setText(f"{month_names[self.current_date.month - 1]} {self.current_date.year}")

        # Update year buttons to show target years
        prev_year = self.current_date.year - 1
        next_year = self.current_date.year + 1
        self.prev_year_btn.setText(f"← {prev_year}")
        self.next_year_btn.setText(f"{next_year} →")

        # Disable next year button if it would go past today's year
        self.next_year_btn.setEnabled(next_year <= date.today().year)

        # Disable prev navigation based on comic's earliest date
        if self.current_comic_name:
            comic_def = get_comic_definition(self.current_comic_name)
            if comic_def and comic_def.earliest_date:
                earliest_month = comic_def.earliest_date.replace(day=1)
                # Prev month: disable if already at the earliest month
                self.prev_month_btn.setEnabled(self.current_date > earliest_month)
                # Prev year: disable if going back a year would be before the earliest year
                self.prev_year_btn.setEnabled(self.current_date.year > comic_def.earliest_date.year)
            else:
                self.prev_month_btn.setEnabled(True)
                self.prev_year_btn.setEnabled(True)
        else:
            self.prev_month_btn.setEnabled(True)
            self.prev_year_btn.setEnabled(True)
        
        # Create day buttons
        self.day_buttons.clear()
        today = date.today()
        
        row = 0
        col = first_weekday
        
        for day in range(1, days_in_month + 1):
            try:
                day_date = date(self.current_date.year, self.current_date.month, day)
                day_button = CalendarDayButton(day, day_date)
                
                # CRITICAL FIX: Set button states - use is_date_available method for consistent behavior
                # This only affects visual appearance, not clickability
                day_button.set_available(self.is_date_available(day_date))
                day_button.set_today(day_date == today)
                day_button.set_selected(day_date == self.selected_date)
                
                # Connect button signal - ensure proper connection for all buttons
                day_button.clicked.connect(lambda checked, d=day_date: self.on_date_clicked(d))
                
                # Add to button group and grid
                self.day_button_group.addButton(day_button)
                self.calendar_grid.addWidget(day_button, row, col)
                self.day_buttons[day_date] = day_button
                
                # Move to next position
                col += 1
                if col > 6:  # End of week
                    col = 0
                    row += 1
            except Exception as e:
                print(f"Error creating button for day {day}: {e}")
                # Continue with next day to ensure calendar is populated
    
    def clear_calendar_grid(self):
        """Clear all widgets from the calendar grid."""
        while self.calendar_grid.count():
            child = self.calendar_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Clear button group
        for button in self.day_button_group.buttons():
            self.day_button_group.removeButton(button)
    
    def on_date_clicked(self, selected_date: date):
        """
        Handle date button clicks.
        
        Args:
            selected_date: The date that was clicked
        """
        # CRITICAL FIX: All dates are now clickable regardless of availability
        # No need to check if date is available before selecting it
        
        # Update selection
        old_selected = self.selected_date
        self.selected_date = selected_date
        
        # Update button states
        if old_selected and old_selected in self.day_buttons:
            self.day_buttons[old_selected].set_selected(False)
        
        if selected_date in self.day_buttons:
            self.day_buttons[selected_date].set_selected(True)
        
        # Emit signal
        self.date_selected.emit(selected_date)
    
    def go_to_previous_month(self):
        """Navigate to the previous month."""
        # Don't go before the comic's start month
        if self.current_comic_name:
            comic_def = get_comic_definition(self.current_comic_name)
            if comic_def and comic_def.earliest_date:
                earliest_month = comic_def.earliest_date.replace(day=1)
                if self.current_date <= earliest_month:
                    return

        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        
        self.populate_calendar()
        self.month_changed.emit(self.current_date.month, self.current_date.year)
    
    def go_to_next_month(self):
        """Navigate to the next month."""
        # Calculate the next month's date
        if self.current_date.month == 12:
            next_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            next_date = self.current_date.replace(month=self.current_date.month + 1)
        
        # Don't allow navigation to future months beyond today
        today = date.today()
        if next_date.year > today.year or (next_date.year == today.year and next_date.month > today.month):
            return
        
        # Update the current date and refresh the calendar
        self.current_date = next_date
        self.populate_calendar()
        self.month_changed.emit(self.current_date.month, self.current_date.year)
    
    def go_to_previous_year(self):
        """Navigate to the previous year, clamping to the comic's earliest month if needed."""
        try:
            prev_year = self.current_date.year - 1
            candidate = self.current_date.replace(year=prev_year)

            if self.current_comic_name:
                comic_def = get_comic_definition(self.current_comic_name)
                if comic_def and comic_def.earliest_date:
                    earliest_month = comic_def.earliest_date.replace(day=1)
                    if candidate < earliest_month:
                        if prev_year < comic_def.earliest_date.year:
                            return  # Already at or before the start year, do nothing
                        candidate = earliest_month  # Clamp to start month

            self.current_date = candidate
            self.clear_calendar_grid()
            self.populate_calendar()
            self.month_changed.emit(self.current_date.month, self.current_date.year)
        except Exception as e:
            print(f"Error navigating to previous year: {e}")
            self.populate_calendar()
    
    def go_to_next_year(self):
        """Navigate to the next year."""
        try:
            # Don't allow navigation to future years beyond today
            today = date.today()
            next_year = self.current_date.year + 1
            if next_year > today.year:
                return
                
            # CRITICAL FIX: Add defensive check for year navigation
            self.current_date = self.current_date.replace(year=next_year)
            self.clear_calendar_grid()
            self.populate_calendar()
            self.month_changed.emit(self.current_date.month, self.current_date.year)
        except Exception as e:
            print(f"Error navigating to next year: {e}")
            # Fallback to ensure calendar remains functional
            self.populate_calendar()
    
    def navigate_to_date(self, target_date: date, emit_signal: bool = True):
        """
        Navigate to a specific date.
        
        Args:
            target_date: The date to navigate to
            emit_signal: Whether to emit the date_selected signal (default True)
        """
        self.current_date = target_date.replace(day=1)  # Set to first day of target month
        self.populate_calendar()
        
        if emit_signal:
            # Always select the target date (regardless of availability)
            self.on_date_clicked(target_date)
        else:
            # Update selection without emitting signal
            old_selected = self.selected_date
            self.selected_date = target_date
            
            # Update button states
            if old_selected and old_selected in self.day_buttons:
                self.day_buttons[old_selected].set_selected(False)
            
            if target_date in self.day_buttons:
                self.day_buttons[target_date].set_selected(True)
    
    def get_selected_date(self) -> Optional[date]:
        """
        Get the currently selected date.
        
        Returns:
            Selected date or None if no date is selected
        """
        return self.selected_date
    
    def set_available_dates(self, available_dates: Set[date]):
        """
        Set the dates that have available comic content.
        
        Args:
            available_dates: Set of dates with available comics
        """
        self.available_dates = available_dates.copy()
        self.populate_calendar()  # Refresh to show availability
    
    def add_available_date(self, date_obj: date):
        """
        Add a single available date.
        
        Args:
            date_obj: Date to mark as available
        """
        self.available_dates.add(date_obj)
        if date_obj in self.day_buttons:
            self.day_buttons[date_obj].set_available(True)
    
    def remove_available_date(self, date_obj: date):
        """
        Remove a date from available dates.
        
        Args:
            date_obj: Date to mark as unavailable
        """
        self.available_dates.discard(date_obj)
        if date_obj in self.day_buttons:
            self.day_buttons[date_obj].set_available(False)
    
    def set_comic_date_range(self, comic_name: str, start_date: date, end_date: Optional[date] = None):
        """
        Set the date range for a specific comic.
        
        Args:
            comic_name: Name of the comic
            start_date: Earliest available date for the comic
            end_date: Latest available date (None for current date)
        """
        if end_date is None:
            end_date = date.today()
        
        self.comic_date_ranges[comic_name] = (start_date, end_date)
    
    def update_available_dates_for_comic(self, comic_name: str):
        """
        Update available dates based on a specific comic's date range.
        
        Args:
            comic_name: Name of the comic to update dates for
        """
        if comic_name not in self.comic_date_ranges:
            return
        
        start_date, end_date = self.comic_date_ranges[comic_name]
        
        # Clear existing available dates
        self.available_dates.clear()
        
        # Add all dates in the range (this is a simplified version)
        # In a real implementation, this would check actual comic availability
        current = start_date
        while current <= end_date:
            self.available_dates.add(current)
            current += timedelta(days=1)
        
        self.populate_calendar()
    
    def is_date_available(self, date_obj: date) -> bool:
        """
        Check if a date has available comic content.
        Uses the complex availability logic defined in the comic's definition.
        """
        if date_obj > date.today():
            return False
        if self.current_comic_name:
            comic_def = get_comic_definition(self.current_comic_name)
            if comic_def:
                return comic_def.is_available(date_obj)
        return True
    
    def get_current_month_year(self) -> tuple[int, int]:
        """
        Get the currently displayed month and year.
        
        Returns:
            Tuple of (month, year)
        """
        return (self.current_date.month, self.current_date.year)
    
    def clear_selection(self):
        """Clear the current date selection."""
        if self.selected_date and self.selected_date in self.day_buttons:
            self.day_buttons[self.selected_date].set_selected(False)
        
        self.selected_date = None
