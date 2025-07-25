"""
Comic controller for integrating UI components with service layer.

This module provides the ComicController class that coordinates between
UI components and the service layer, handling asynchronous operations,
error management, and state synchronization.
"""

import logging
from datetime import date, datetime
from typing import Optional, Set
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtWidgets import QMessageBox

from models.data_models import ComicData, get_comic_definition, COMIC_DEFINITIONS
from services.comic_service import ComicService, ComicServiceError
from services.error_handler import ComicUnavailableError, NetworkError, ParsingError


class ComicLoadingWorker(QThread):
    """
    Background worker thread for loading comics without blocking the UI.
    
    This worker handles comic retrieval operations in a separate thread
    to keep the UI responsive during network operations.
    """
    
    # Signals for communicating with the main thread
    comic_loaded = pyqtSignal(ComicData)  # Emitted when comic is successfully loaded
    loading_failed = pyqtSignal(Exception)  # Emitted when loading fails
    loading_progress = pyqtSignal(str)  # Emitted with progress messages
    
    def __init__(self, comic_service: ComicService, comic_name: str, comic_date: date):
        """
        Initialize the comic loading worker.
        
        Args:
            comic_service: ComicService instance for comic retrieval
            comic_name: Name of the comic to load
            comic_date: Date of the comic to load
        """
        super().__init__()
        self.comic_service = comic_service
        self.comic_name = comic_name
        self.comic_date = comic_date
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Load the comic in the background thread."""
        try:
            self.loading_progress.emit("Checking cache...")
            
            # Check if comic is cached first
            if self.comic_service.is_comic_cached(self.comic_name, self.comic_date):
                self.loading_progress.emit("Loading from cache...")
            else:
                self.loading_progress.emit("Downloading comic...")
            
            # Load the comic
            comic_data = self.comic_service.get_comic(self.comic_name, self.comic_date)
            
            self.loading_progress.emit("Comic loaded successfully")
            self.comic_loaded.emit(comic_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load comic {self.comic_name} for {self.comic_date}: {e}")
            self.loading_failed.emit(e)


class ComicController(QObject):
    """
    Controller for coordinating UI components with the service layer.
    
    This class handles:
    - Comic selection and loading coordination
    - Date navigation and availability updates
    - Asynchronous comic loading with progress feedback
    - Error handling and user feedback
    - State synchronization between UI components
    """
    
    # Signals for UI coordination
    comic_loading_started = pyqtSignal(str, date)  # comic_name, date
    comic_loading_finished = pyqtSignal(str, date)  # comic_name, date
    comic_loaded = pyqtSignal(ComicData)  # Successfully loaded comic
    loading_error = pyqtSignal(str, str, str)  # error_message, recovery_suggestions, error_type
    available_dates_updated = pyqtSignal(str, set)  # comic_name, available_dates
    
    def __init__(self, comic_service: Optional[ComicService] = None):
        """
        Initialize the comic controller.
        
        Args:
            comic_service: ComicService instance (creates new one if None)
        """
        super().__init__()
        self.comic_service = comic_service or ComicService()
        self.logger = logging.getLogger(__name__)
        
        # Current state
        self.current_comic_name: Optional[str] = None
        self.current_date: Optional[date] = None
        self.loading_worker: Optional[ComicLoadingWorker] = None
        
        # Available dates cache for each comic
        self.available_dates_cache: dict[str, Set[date]] = {}
        
        # Initialize service if needed
        self.initialization_timer = QTimer()
        self.initialization_timer.setSingleShot(True)
        self.initialization_timer.timeout.connect(self._initialize_service)
        self.initialization_timer.start(100)  # Start initialization after UI is ready
    
    def _initialize_service(self):
        """Initialize the comic service in the background."""
        try:
            self.logger.info("Initializing comic service...")
            
            # Check if initialization is needed
            if self.comic_service.initialize_if_needed():
                self.logger.info("Comic service initialization completed")
                # Update available dates for all comics
                self._update_all_available_dates()
            else:
                self.logger.info("Comic service already initialized")
                # Still update available dates from config
                self._update_all_available_dates()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize comic service: {e}")
            error_msg = self.comic_service.get_user_friendly_error_message(e)
            suggestions = self.comic_service.get_recovery_suggestions(e)
            self.loading_error.emit(error_msg, "; ".join(suggestions), "network")
    
    def _update_all_available_dates(self):
        """Update available dates for all comics based on configuration."""
        for comic_def in COMIC_DEFINITIONS:
            self._update_available_dates_for_comic(comic_def.name)
    
    def _update_available_dates_for_comic(self, comic_name: str):
        """
        Update available dates for a specific comic.
        
        Args:
            comic_name: Name of the comic to update
        """
        try:
            # Get start date from configuration
            start_date = self.comic_service.config_manager.get_start_date(comic_name)
            if not start_date:
                # If no start date, assume comic is available from a reasonable default
                start_date = date(2000, 1, 1)  # Default fallback
            
            # Generate available dates from start date to today
            available_dates = set()
            current = start_date
            today = date.today()
            
            # For performance, we'll only generate dates for the current year and previous year
            # In a real application, this would be more sophisticated
            year_start = date(today.year - 1, 1, 1)
            if start_date > year_start:
                current = start_date
            else:
                current = year_start
            
            while current <= today:
                available_dates.add(current)
                # Use timedelta for proper date arithmetic
                from datetime import timedelta
                current = current + timedelta(days=1)
                
                # Safety check to prevent infinite loops
                if len(available_dates) > 1000:
                    break
            
            # Cache and emit the available dates
            self.available_dates_cache[comic_name] = available_dates
            self.available_dates_updated.emit(comic_name, available_dates)
            
        except Exception as e:
            self.logger.error(f"Failed to update available dates for {comic_name}: {e}")
    
    def select_comic(self, comic_name: str):
        """
        Handle comic selection from the UI.
        
        Args:
            comic_name: Name of the selected comic
        """
        self.logger.info(f"Comic selected: {comic_name}")
        self.current_comic_name = comic_name
        
        # Update available dates for the selected comic
        self._update_available_dates_for_comic(comic_name)
        
        # Load current date's comic if we have a date selected
        if self.current_date:
            self.load_comic(comic_name, self.current_date)
        else:
            # Load today's comic by default
            self.load_comic(comic_name, date.today())
    
    def select_date(self, selected_date: date):
        """
        Handle date selection from the calendar.
        
        Args:
            selected_date: Date selected from the calendar
        """
        self.logger.info(f"Date selected: {selected_date}")
        self.current_date = selected_date
        
        # Load comic for the selected date if we have a comic selected
        if self.current_comic_name:
            self.load_comic(self.current_comic_name, selected_date)
    
    def load_comic(self, comic_name: str, comic_date: date):
        """
        Load a comic for a specific date asynchronously.
        
        Args:
            comic_name: Name of the comic to load
            comic_date: Date of the comic to load
        """
        # Cancel any existing loading operation
        if self.loading_worker and self.loading_worker.isRunning():
            self.loading_worker.quit()
            self.loading_worker.wait()
        
        # Check if comic service is available
        if not self.comic_service:
            error_msg = "Comic service is currently unavailable"
            suggestions = "Please restart the application or check your internet connection"
            self.loading_error.emit(error_msg, suggestions, "network")
            return
        
        # Validate comic availability
        if not self.comic_service.validate_comic_availability(comic_name, comic_date):
            error_msg = f"Comic '{comic_name}' is not available for {comic_date.strftime('%B %d, %Y')}"
            suggestions = "Try selecting a different date or comic"
            self.loading_error.emit(error_msg, suggestions, "unavailable")
            return
        
        self.logger.info(f"Loading comic {comic_name} for {comic_date}")
        
        # Update current state
        self.current_comic_name = comic_name
        self.current_date = comic_date
        
        # Emit loading started signal
        self.comic_loading_started.emit(comic_name, comic_date)
        
        # Start loading in background thread
        self.loading_worker = ComicLoadingWorker(self.comic_service, comic_name, comic_date)
        self.loading_worker.comic_loaded.connect(self._on_comic_loaded)
        self.loading_worker.loading_failed.connect(self._on_loading_failed)
        self.loading_worker.loading_progress.connect(self._on_loading_progress)
        self.loading_worker.start()
    
    @pyqtSlot(ComicData)
    def _on_comic_loaded(self, comic_data: ComicData):
        """
        Handle successful comic loading.
        
        Args:
            comic_data: Loaded comic data
        """
        self.logger.info(f"Comic loaded successfully: {comic_data.comic_name} for {comic_data.date}")
        
        # Emit signals
        self.comic_loaded.emit(comic_data)
        self.comic_loading_finished.emit(comic_data.comic_name, comic_data.date)
    
    @pyqtSlot(Exception)
    def _on_loading_failed(self, error: Exception):
        """
        Handle comic loading failure.
        
        Args:
            error: Exception that occurred during loading
        """
        self.logger.error(f"Comic loading failed: {error}")
        
        # Determine error type for appropriate UI handling
        error_type = self._classify_error(error)
        
        # Get user-friendly error message and suggestions
        error_msg = self.comic_service.get_user_friendly_error_message(error)
        suggestions = self.comic_service.get_recovery_suggestions(error)
        
        # Emit error signal with error type
        self.loading_error.emit(error_msg, "; ".join(suggestions), error_type)
        
        # Emit loading finished signal
        if self.current_comic_name and self.current_date:
            self.comic_loading_finished.emit(self.current_comic_name, self.current_date)
    
    def _classify_error(self, error: Exception) -> str:
        """
        Classify error type for appropriate UI handling.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error type string for UI handling
        """
        if isinstance(error, ComicUnavailableError):
            return "unavailable"
        elif isinstance(error, NetworkError):
            return "network"
        elif isinstance(error, ParsingError):
            return "parsing"
        elif hasattr(error, '__class__') and 'network' in error.__class__.__name__.lower():
            return "network"
        elif hasattr(error, '__class__') and 'connection' in error.__class__.__name__.lower():
            return "network"
        elif hasattr(error, '__class__') and 'timeout' in error.__class__.__name__.lower():
            return "network"
        else:
            return "general"
    
    @pyqtSlot(str)
    def _on_loading_progress(self, progress_message: str):
        """
        Handle loading progress updates.
        
        Args:
            progress_message: Progress message to display
        """
        self.logger.debug(f"Loading progress: {progress_message}")
        # Progress messages are handled by the UI components directly
    
    def get_available_dates(self, comic_name: str) -> Set[date]:
        """
        Get available dates for a specific comic.
        
        Args:
            comic_name: Name of the comic
            
        Returns:
            Set of available dates for the comic
        """
        return self.available_dates_cache.get(comic_name, set())
    
    def is_date_available(self, comic_name: str, comic_date: date) -> bool:
        """
        Check if a comic is available for a specific date.
        
        Args:
            comic_name: Name of the comic
            comic_date: Date to check
            
        Returns:
            True if comic is available for the date
        """
        available_dates = self.get_available_dates(comic_name)
        return comic_date in available_dates
    
    def retry_current_comic(self):
        """Retry loading the current comic."""
        if self.current_comic_name and self.current_date:
            self.load_comic(self.current_comic_name, self.current_date)
    
    def get_current_comic_name(self) -> Optional[str]:
        """Get the currently selected comic name."""
        return self.current_comic_name
    
    def get_current_date(self) -> Optional[date]:
        """Get the currently selected date."""
        return self.current_date
    
    def get_comic_service(self) -> ComicService:
        """Get the comic service instance."""
        return self.comic_service
    
    def set_comic_service(self, comic_service: ComicService):
        """
        Set the comic service instance (for dependency injection).
        
        Args:
            comic_service: ComicService instance to use
        """
        self.comic_service = comic_service
        self.logger.info("Comic service injected into controller")
        
        # Re-initialize with the new service
        self._initialize_service()
    
    def show_error_dialog(self, title: str, message: str, suggestions: str = ""):
        """
        Show an error dialog to the user.
        
        Args:
            title: Dialog title
            message: Error message
            suggestions: Recovery suggestions (optional)
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if suggestions:
            msg_box.setInformativeText(f"Suggestions: {suggestions}")
        
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def cleanup(self):
        """Clean up resources when the controller is destroyed."""
        if self.loading_worker and self.loading_worker.isRunning():
            self.loading_worker.quit()
            self.loading_worker.wait()
        
        if self.initialization_timer.isActive():
            self.initialization_timer.stop()