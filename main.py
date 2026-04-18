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
from version import __version__


class ComicStripBrowser:
    """Main application class for the Comic Strip Browser."""
    
    def __init__(self):
        """Initialize the comic strip browser application."""
        self.app = None
        self.main_window = None
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
        # PORTAL & GIO BYPASS: These fix library/DBus errors seen in GNOME.
        # We keep them here so the app works correctly even when run from terminal.
        os.environ["QT_NO_XDG_DESKTOP_PORTAL"] = "1"
        os.environ["GIO_USE_VFS"] = "local"
        os.environ["GIO_USE_VOLUME_MONITOR"] = "unix"
        os.environ["GIO_MODULE_DIR"] = ""

        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Comic Strip Browser")
        self.app.setApplicationVersion(__version__)
        self.app.setOrganizationName("Comic Browser")

        # Connect application aboutToQuit signal for cleanup
        self.app.aboutToQuit.connect(self.shutdown)
    
    def initialize_main_window(self):
        """Initialize and show the main window."""
        try:
            self.main_window = MainWindow()
            self.main_window.show()
        except Exception as e:
            self.show_error_dialog("Startup Error", f"Failed to initialize main window: {e}")
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
            # Cleanup main window
            if self.main_window:
                self.main_window.close()
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

            # Show the main window
            self.initialize_main_window()

            # Start the application event loop
            return self.app.exec()
        except Exception as e:
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
