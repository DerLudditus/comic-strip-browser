#!/usr/bin/env python3
"""
Comic Strip Browser - Main Entry Point

A standalone PyQt6 application for browsing comic strips from GoComics.com.
Supports 15 predefined comic strips with calendar navigation and caching.
"""

import sys
import logging
import atexit
import signal
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from ui.main_window import MainWindow
from services.config_manager import ConfigManager
from services.cache_manager import CacheManager
from services.comic_service import ComicService
from services.date_manager import DateManager
from services.web_scraper import WebScraper
from services.error_handler import ErrorHandler


class InitializationWorker(QThread):
    """Worker thread for application initialization tasks."""
    
    progress_updated = pyqtSignal(str, int)  # message, percentage
    initialization_complete = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, comic_service):
        super().__init__()
        self.comic_service = comic_service
        self.logger = logging.getLogger(__name__)
            
    def run(self):
        """Run initialization tasks in background thread."""
        try:
            self.progress_updated.emit("Initializing configuration...", 10)
            
            # Configuration is already loaded in ComicService constructor
            self.progress_updated.emit("Verifying cache integrity...", 30)
            
            # Cache integrity is verified in CacheManager constructor
            self.progress_updated.emit("Checking for first-run setup...", 50)
            
            # Configuration is automatically populated with hard-coded dates
            self.progress_updated.emit("Loading comic configuration...", 80)
            self.logger.info("Using hard-coded comic start dates - no discovery needed")
            
            self.progress_updated.emit("Initialization complete", 100)
            self.initialization_complete.emit(True, "Application initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            self.initialization_complete.emit(False, f"Initialization failed: {e}")


class ComicStripBrowser:
    """Main application class for the Comic Strip Browser."""
    
    def __init__(self):
        """Initialize the comic strip browser application."""
        self.app = None
        self.main_window = None
        self.services_initialized = False
        
        # Service instances
        self.config_manager = None
        self.cache_manager = None
        self.error_handler = None
        self.web_scraper = None
        self.date_manager = None
        self.comic_service = None
        
        # Initialization components
        self.initialization_worker = None
        self.progress_dialog = None
        
        self.setup_logging()
        self.setup_signal_handlers()
        
    def setup_logging(self):
        """Set up enhanced logging for the application."""
        from services.logging_service import setup_logging
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Set up enhanced logging service
        self.logging_service = setup_logging(str(log_dir), "comic_browser")
        self.logger = self.logging_service.get_logger("app")
        
        self.logger.info("Comic Strip Browser starting up with enhanced logging")
        
        # Log system information
        import platform
        system_info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0]
        }
        self.logging_service.log_system_state("startup", system_info)
        
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            self.shutdown()
            sys.exit(0)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register atexit handler for cleanup
        atexit.register(self.cleanup_on_exit)
        
    def initialize_application(self):
        """Initialize the PyQt6 application."""
        self.logger.info("Initializing PyQt6 application")
        
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Comic Strip Browser")
        self.app.setApplicationVersion("1.0.4")
        self.app.setOrganizationName("Comic Browser")
        
        # Set application properties for cross-platform compatibility
        if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
            self.app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
            self.app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        
        # Connect application aboutToQuit signal for cleanup
        self.app.aboutToQuit.connect(self.shutdown)
        
        self.logger.info("PyQt6 application initialized")
    
    def initialize_services(self):
        """Initialize all service layer components in proper order."""
        self.logger.info("Initializing service layer components")
        
        try:
            # Initialize services in dependency order
            self.error_handler = ErrorHandler()
            self.config_manager = ConfigManager()
            self.cache_manager = CacheManager(error_handler=self.error_handler)
            self.web_scraper = WebScraper(error_handler=self.error_handler)
            self.date_manager = DateManager(
                web_scraper=self.web_scraper,
                config_manager=self.config_manager
            )
            self.comic_service = ComicService(
                web_scraper=self.web_scraper,
                cache_manager=self.cache_manager,
                config_manager=self.config_manager,
                date_manager=self.date_manager,
                error_handler=self.error_handler
            )
            
            self.services_initialized = True
            self.logger.info("Service layer components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise
    
    def validate_configuration(self):
        """Validate application configuration and dependencies."""
        self.logger.info("Validating application configuration")
        
        try:
            # Check if config file exists and is readable
            config_path = self.config_manager.get_config_file_path()
            if not config_path.exists():
                self.logger.info("Configuration file does not exist, will be created")
            
            # Validate cache directory
            cache_dir = Path("cache")
            if not cache_dir.exists():
                cache_dir.mkdir(exist_ok=True)
                self.logger.info("Created cache directory")
            
            # Check write permissions
            test_file = cache_dir / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                self.logger.info("Cache directory write permissions verified")
            except Exception as e:
                self.logger.error(f"Cache directory not writable: {e}")
                raise
            
            self.logger.info("Configuration validation completed")
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
    
    def show_initialization_progress(self):
        """Show initialization progress dialog."""
        self.progress_dialog = QProgressDialog(
            "Initializing Comic Strip Browser...",
            None,  # No cancel button to avoid auto-cancel issues
            0, 100
        )
        self.progress_dialog.setWindowTitle("Comic Strip Browser")
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setCancelButton(None)  # Explicitly disable cancel button
        self.progress_dialog.show()
    
    def on_initialization_canceled(self):
        """Handle initialization cancellation."""
        self.logger.info("User requested initialization cancellation")
        if self.initialization_worker and self.initialization_worker.isRunning():
            self.initialization_worker.terminate()
            self.initialization_worker.wait()
        
        self.shutdown()
        sys.exit(1)
    
    def run_background_initialization(self):
        """Run initialization tasks directly (no threading to avoid Qt issues in binary)."""
        self.logger.info("Starting initialization")
        
        try:
            # Run initialization directly instead of in a separate thread
            self.on_initialization_progress("Initializing configuration...", 10)
            self.on_initialization_progress("Verifying cache integrity...", 30)
            self.on_initialization_progress("Checking for first-run setup...", 50)
            self.on_initialization_progress("Loading comic configuration...", 80)
            self.logger.info("Using hard-coded comic start dates - no discovery needed")
            self.on_initialization_progress("Initialization complete", 100)
            
            # Complete initialization successfully
            self.on_initialization_complete(True, "Application initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            self.on_initialization_complete(False, f"Initialization failed: {e}")
    
    def on_initialization_progress(self, message: str, percentage: int):
        """Handle initialization progress updates."""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            self.progress_dialog.setValue(percentage)
        
        self.logger.debug(f"Initialization progress: {message} ({percentage}%)")
    
    def on_initialization_complete(self, success: bool, message: str):
        """Handle initialization completion."""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        if success:
            self.logger.info(f"Initialization completed successfully: {message}")
            self.initialize_main_window()
        else:
            self.logger.error(f"Initialization failed: {message}")
            self.show_error_dialog("Initialization Error", message)
            self.shutdown()
            sys.exit(1)
    
    def show_error_dialog(self, title: str, message: str):
        """Show error dialog to user."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def initialize_main_window(self):
        """Initialize the main window with services."""
        self.logger.info("Initializing main window")
        
        try:
            self.main_window = MainWindow()
            
            # Inject services into the main window's controller
            if hasattr(self.main_window, 'comic_controller') and self.main_window.comic_controller:
                controller = self.main_window.comic_controller
                if hasattr(controller, 'set_comic_service'):
                    controller.set_comic_service(self.comic_service)
                    self.logger.info("Comic service injected into controller")
            
            self.main_window.show()
            self.logger.info("Main window displayed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize main window: {e}")
            self.show_error_dialog("Startup Error", f"Failed to initialize main window: {e}")
            raise
    
    def is_first_run(self) -> bool:
        """Check if this is the first run of the application."""
        if not self.config_manager:
            return True
        
        return not self.config_manager.has_all_start_dates()
    
    def shutdown(self):
        """Perform graceful application shutdown."""
        self.logger.info("Starting application shutdown")
        
        try:
            # Stop any running background tasks
            if self.initialization_worker and self.initialization_worker.isRunning():
                self.logger.info("Stopping initialization worker")
                self.initialization_worker.terminate()
                self.initialization_worker.wait(3000)  # Wait up to 3 seconds
            
            # Close progress dialog if open
            if self.progress_dialog:
                self.progress_dialog.close()
            
            # Cleanup main window
            if self.main_window:
                self.logger.info("Closing main window")
                self.main_window.close()
            
            # Cleanup services
            if self.services_initialized:
                self.cleanup_services()
            
            self.logger.info("Application shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def cleanup_services(self):
        """Clean up service layer components."""
        self.logger.info("Cleaning up service layer")
        
        try:
            # Clear error statistics
            if self.error_handler:
                self.error_handler.clear_error_statistics()
            
            # No explicit cleanup needed for other services as they handle
            # their own resource management through proper file handling
            
            self.logger.info("Service layer cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during service cleanup: {e}")
    
    def cleanup_on_exit(self):
        """Cleanup function called on application exit."""
        self.logger.info("Performing final cleanup on exit")
        self.shutdown()
    
    def run(self):
        """Start the application main loop."""
        try:
            # Initialize PyQt6 application
            self.initialize_application()
            
            # Initialize service layer
            self.initialize_services()
            
            # Validate configuration
            self.validate_configuration()
            
            # Show progress dialog and start background initialization
            self.show_initialization_progress()
            
            # Use QTimer to start background initialization after event loop starts
            QTimer.singleShot(100, self.run_background_initialization)
            
            # Start the application event loop
            self.logger.info("Starting application event loop")
            return self.app.exec()
            
        except Exception as e:
            self.logger.error(f"Fatal error during application startup: {e}")
            if self.app:
                self.show_error_dialog("Startup Error", f"Fatal error during startup: {e}")
            return 1


def main():
    """Main entry point for the application."""
    try:
        browser = ComicStripBrowser()
        return browser.run()
    except Exception as e:
        print(f"Error starting Comic Strip Browser: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
