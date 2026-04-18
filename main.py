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
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from services.config_manager import ConfigManager
from services.cache_manager import CacheManager
from services.comic_service import ComicService
from services.date_manager import DateManager
from services.web_scraper import WebScraper
from services.error_handler import ErrorHandler
from version import __version__


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
        # PORTAL & GIO BYPASS: These fix library/DBus errors seen in modern Linux 
        # when running PyInstaller bundles.
        os.environ["QT_NO_XDG_DESKTOP_PORTAL"] = "1"
        os.environ["GIO_USE_VFS"] = "local"
        os.environ["GIO_USE_VOLUME_MONITOR"] = "unix"
        os.environ["GIO_MODULE_DIR"] = ""

        self.app = QApplication(sys.argv)
        
        # Consistent IDs for Linux desktop integration
        if sys.platform == "linux":
            self.app.setDesktopFileName("comic-strip-browser")
            self.app.setApplicationName("comic-strip-browser")
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
            cache_dir = Path("cache")
            if not cache_dir.exists():
                cache_dir.mkdir(exist_ok=True)
            
            test_file = cache_dir / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                raise
        except Exception as e:
            raise
    
    def show_error_dialog(self, title: str, message: str):
        """Show error dialog to user."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def shutdown(self):
        """Perform graceful application shutdown."""
        try:
            if self.main_window:
                self.main_window.close()
            if self.services_initialized:
                self.cleanup_services()
        except Exception:
            pass
    
    def cleanup_services(self):
        """Clean up service layer components."""
        try:
            if self.error_handler:
                self.error_handler.clear_error_statistics()
        except Exception:
            pass
    
    def cleanup_on_exit(self):
        """Cleanup function called on application exit."""
        self.shutdown()

    def run(self):
        """Start the application main loop."""
        try:
            # Initialize PyQt6 application
            self.initialize_application()

            # Initialize services and configuration
            self.initialize_services()
            self.validate_configuration()

            # Create main window
            self.main_window = MainWindow()

            # Inject initialized services into the controller
            if hasattr(self.main_window, 'comic_controller') and self.main_window.comic_controller:
                self.main_window.comic_controller.set_comic_service(self.comic_service)

            # Show window
            self.main_window.show()

            # Start the application event loop
            return self.app.exec()
        except Exception as e:
            if self.app:
                self.show_error_dialog("Startup Error", f"Fatal error during startup: {e}")
            else:
                print(f"Startup Error: {e}")
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
