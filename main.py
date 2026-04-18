#!/usr/bin/env python3
"""
Comic Strip Browser - Main Entry Point

A standalone PyQt6 application for browsing comic strips from from GoComics and Comics Kingdom.
Supports 40 predefined comic strips with calendar navigation and caching.
"""

import sys
import atexit
import signal
import os
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
from version import __version__


class InitializationWorker(QThread):
    """Worker thread for application initialization tasks."""
    
    progress_updated = pyqtSignal(str, int)  # message, percentage
    initialization_complete = pyqtSignal(bool, str, object)  # success, message, comic_service
    
    def __init__(self, browser_instance):
        super().__init__()
        self.browser = browser_instance
            
    def run(self):
        """Run initialization tasks in background thread."""
        try:
            self.progress_updated.emit("Initializing configuration...", 20)
            self.browser.initialize_services()
            
            self.progress_updated.emit("Verifying cache integrity...", 60)
            self.browser.validate_configuration()
            
            self.progress_updated.emit("Initialization complete", 100)
            self.initialization_complete.emit(True, "Application initialized successfully", self.browser.comic_service)
            
        except Exception as e:
            self.initialization_complete.emit(False, f"Initialization failed: {e}", None)


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
        
        self.setup_signal_handlers()
        

        
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.shutdown()
            sys.exit(0)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register atexit handler for cleanup
        atexit.register(self.cleanup_on_exit)
        
    def initialize_application(self):
        """Initialize the PyQt6 application."""
        # SILENT STARTUP: Scrub all startup/activation tokens to prevent 
        # the compositor from showing a "Wait" cursor.
        for env_var in ["DESKTOP_STARTUP_ID", "XDG_ACTIVATION_TOKEN", "XDG_ACTIVATION_ID"]:
            os.environ.pop(env_var, None)

        # PORTAL & GIO BYPASS: Disable XDG Desktop Portal and GVFS integration. 
        # This prevents library conflicts and DBus delays caused by PyInstaller's 
        # bundled glib conflicting with the host system's gvfs modules.
        os.environ["QT_NO_XDG_DESKTOP_PORTAL"] = "1"
        os.environ["GIO_USE_VFS"] = "local"
        os.environ["GIO_USE_VOLUME_MONITOR"] = "unix"
        os.environ["GIO_MODULE_DIR"] = ""

        self.app = QApplication(sys.argv)
        
        # Consistent IDs for Linux desktop integration
        if sys.platform == "linux":
            self.app.setDesktopFileName("comic-strip-browser")
            self.app.setApplicationName("Comic Strip Browser")
        else:
            self.app.setApplicationName("Comic Strip Browser")

        self.app.setApplicationVersion(__version__)
        self.app.setOrganizationName("Comic Browser")

        # Connect application aboutToQuit signal for cleanup
        self.app.aboutToQuit.connect(self.shutdown)
    
    def initialize_services(self):
        """Initialize all service layer components in proper order."""
        
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
            
        except Exception as e:
            raise
    
    def validate_configuration(self):
        """Validate application configuration and dependencies."""
        
        try:
            # Validate cache directory
            cache_dir = Path("cache")
            if not cache_dir.exists():
                cache_dir.mkdir(exist_ok=True)
            
            # Check write permissions
            test_file = cache_dir / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                raise
            
        except Exception as e:
            raise
    
    def on_initialization_complete(self, success: bool, message: str, comic_service):
        """Handle initialization completion."""
        if success:
            # Inject the now-ready services into the controller
            if hasattr(self.main_window, 'comic_controller') and self.main_window.comic_controller:
                controller = self.main_window.comic_controller
                if hasattr(controller, 'set_comic_service'):
                    controller.set_comic_service(comic_service)
        else:
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
        """Initialize and show the main window immediately."""
        try:
            self.main_window = MainWindow()
            self.main_window.show()
        except Exception as e:
            self.show_error_dialog("Startup Error", f"Failed to initialize main window: {e}")
            raise
    
    def is_first_run(self) -> bool:
        """Check if this is the first run of the application."""
        if not self.config_manager:
            return True
        
        return not self.config_manager.has_all_start_dates()
    
    def shutdown(self):
        """Perform graceful application shutdown."""
        
        try:
            # Stop any running background tasks
            if self.initialization_worker and self.initialization_worker.isRunning():
                self.initialization_worker.terminate()
                self.initialization_worker.wait(3000)  # Wait up to 3 seconds
            
            # Cleanup main window
            if self.main_window:
                self.main_window.close()
            
            # Cleanup services
            if self.services_initialized:
                self.cleanup_services()
            
        except Exception as e:
            pass
    
    def cleanup_services(self):
        """Clean up service layer components."""
        try:
            # Clear error statistics
            if self.error_handler:
                self.error_handler.clear_error_statistics()
            
        except Exception as e:
            pass
    
    def cleanup_on_exit(self):
        """Cleanup function called on application exit."""
        self.shutdown()

    def run(self):
        """Start the application main loop."""
        try:
            # Initialize PyQt6 application
            self.initialize_application()

            # Show the main window immediately
            self.initialize_main_window()

            # Force the cursor to be a normal arrow immediately.
            self.app.setOverrideCursor(Qt.CursorShape.ArrowCursor)
            QTimer.singleShot(1000, self.app.restoreOverrideCursor)

            # Start background initialization using status bar instead of dialog
            self.initialization_worker = InitializationWorker(self)
            self.initialization_worker.progress_updated.connect(self._on_bg_init_progress)
            self.initialization_worker.initialization_complete.connect(self.on_initialization_complete)
            self.initialization_worker.start()

            # Start the application event loop
            return self.app.exec()

        except Exception as e:
            if self.app:
                self.show_error_dialog("Startup Error", f"Fatal error during startup: {e}")
            return 1

    def _on_bg_init_progress(self, message: str, percentage: int):
        """Update progress in the main window status bar."""
        if self.main_window:
            self.main_window.update_status(f"{message} ({percentage}%)")


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
