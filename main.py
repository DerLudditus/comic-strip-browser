#!/usr/bin/env python3
"""
Comic Strip Browser - Main Entry Point

A standalone PyQt6 application for browsing comic strips from from GoComics and Comics Kingdom.
Supports 80 predefined comic strips with calendar navigation and caching.
Also supports headless CLI execution for batch caching and metadata queries.
"""

import sys
import atexit
import signal
import os
import argparse
from datetime import date, timedelta
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from models.data_models import COMIC_DEFINITIONS, get_comic_definition
from services.config_manager import ConfigManager
from services.cache_manager import CacheManager
from services.comic_service import ComicService
from services.date_manager import DateManager
from services.web_scraper import WebScraper
from services.error_handler import ErrorHandler
from version import __version__


def _attach_console():
    """Attach to parent console on Windows so CLI output is visible in command prompt/PowerShell."""
    if sys.platform == "win32":
        try:
            import ctypes
            # ATTACH_PARENT_PROCESS = -1
            if ctypes.windll.kernel32.AttachConsole(-1):
                try:
                    if sys.stdout is None or not sys.stdout.writable():
                        sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                except Exception:
                    pass
                try:
                    if sys.stderr is None or not sys.stderr.writable():
                        sys.stderr = open("CONOUT$", "w", encoding="utf-8")
                except Exception:
                    pass
        except Exception:
            pass


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

        # Log active typeface when debug logging is enabled
        import logging
        from PyQt6.QtGui import QFont, QFontInfo, QPalette, QColor
        from ui import get_font_families
        logger = logging.getLogger("main.ComicStripBrowser")
        system_family = self.app.font().family()
        font = QFont()
        font.setFamilies(get_font_families())
        resolved_family = QFontInfo(font).family()
        if system_family:
            logger.info(f"Using default typeface '{resolved_family}'")
        else:
            fallback_chain_str = ", ".join(f"'{f}'" for f in get_font_families())
            logger.info(f"Could not query default typeface; fallback chain: {fallback_chain_str}")

        # Force a light palette to prevent dark DE themes from breaking
        # the hardcoded light-color UI (borders, backgrounds, text).
        palette = self.app.palette()
        if palette.color(QPalette.ColorRole.Window).lightness() < 128:
            logger.info("Dark theme detected — forcing light palette")
            light = QPalette()
            light.setColor(QPalette.ColorRole.Window, QColor(239, 239, 239))
            light.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
            light.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
            light.setColor(QPalette.ColorRole.AlternateBase, QColor(239, 239, 239))
            light.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
            light.setColor(QPalette.ColorRole.Button, QColor(239, 239, 239))
            light.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
            light.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
            light.setColor(QPalette.ColorRole.Highlight, QColor(33, 150, 243))
            light.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            light.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
            light.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
            self.app.setPalette(light)

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


def _find_latest_available_date(comic_def, target_date: date, max_days: int = 31) -> date:
    """Find the most recent available publication date for a comic on or before target_date."""
    if comic_def.is_available(target_date):
        return target_date
    search_date = target_date
    for _ in range(max_days):
        search_date -= timedelta(days=1)
        if comic_def.is_available(search_date):
            return search_date
    return comic_def.earliest_date if comic_def.earliest_date else target_date


def handle_cli(args) -> int:
    """Handle command line operations without GUI."""
    _attach_console()

    # --names: Print all internal comic names
    if args.names:
        for comic_def in COMIC_DEFINITIONS:
            print(comic_def.name)
        return 0

    # --info: Print all numbered comics with internal name and display name
    if args.info:
        for i, comic_def in enumerate(COMIC_DEFINITIONS, start=1):
            print(f"number={i} | name={comic_def.name} | display_name={comic_def.display_name}")
        return 0

    # Determine target date: --yesterday or default to --today
    target_date = date.today() - timedelta(days=1) if args.yesterday else date.today()

    # Initialize headless services for downloading
    browser = ComicStripBrowser()
    try:
        browser.initialize_services()
        browser.validate_configuration()
    except Exception as e:
        print(f"Initialization error: {e}", file=sys.stderr)
        return 1

    # --all: Download all comics for target date (or latest available)
    if args.all:
        total = len(COMIC_DEFINITIONS)
        print(f"Downloading all {total} comics for {target_date.isoformat()}...")
        successful = 0
        failed = 0

        for i, comic_def in enumerate(COMIC_DEFINITIONS, start=1):
            fetch_date = _find_latest_available_date(comic_def, target_date)
            date_note = f" (latest: {fetch_date.isoformat()})" if fetch_date != target_date else ""
            try:
                comic_data = browser.comic_service.get_comic(comic_def.name, fetch_date)
                saved_location = comic_data.cached_image_path or "cached"
                print(f"[{i:02d}/{total}] {comic_def.name}: OK{date_note} -> {saved_location}")
                successful += 1
            except Exception as e:
                print(f"[{i:02d}/{total}] {comic_def.name}: Failed ({e})")
                failed += 1

        print(f"\nCompleted: {successful} succeeded, {failed} failed out of {total} comics.")
        return 0 if failed == 0 else 1

    # --name: Download single comic by name
    if args.name is not None:
        comic_name = args.name.strip().lower()
        comic_def = get_comic_definition(comic_name)
        if not comic_def:
            print(f"Error: Unknown comic name '{args.name}'. Use --names or --info to view available comics.", file=sys.stderr)
            return 1

        fetch_date = _find_latest_available_date(comic_def, target_date)
        date_note = f" (latest: {fetch_date.isoformat()})" if fetch_date != target_date else ""
        print(f"Downloading {comic_def.display_name} ({comic_def.name}) for {fetch_date.isoformat()}...")
        try:
            comic_data = browser.comic_service.get_comic(comic_def.name, fetch_date)
            saved_location = comic_data.cached_image_path or "cached"
            print(f"Successfully downloaded {comic_def.display_name}{date_note}: {saved_location}")
            return 0
        except Exception as e:
            print(f"Error downloading {comic_def.display_name} for {fetch_date.isoformat()}: {e}", file=sys.stderr)
            return 1

    # --number: Download single comic by number (1-80)
    if args.number is not None:
        num = args.number
        if num < 1 or num > len(COMIC_DEFINITIONS):
            print(f"Error: Comic number {num} is out of range (1-{len(COMIC_DEFINITIONS)}). Use --info to view the list.", file=sys.stderr)
            return 1

        comic_def = COMIC_DEFINITIONS[num - 1]
        fetch_date = _find_latest_available_date(comic_def, target_date)
        date_note = f" (latest: {fetch_date.isoformat()})" if fetch_date != target_date else ""
        print(f"Downloading #{num} {comic_def.display_name} ({comic_def.name}) for {fetch_date.isoformat()}...")
        try:
            comic_data = browser.comic_service.get_comic(comic_def.name, fetch_date)
            saved_location = comic_data.cached_image_path or "cached"
            print(f"Successfully downloaded #{num} {comic_def.display_name}{date_note}: {saved_location}")
            return 0
        except Exception as e:
            print(f"Error downloading #{num} {comic_def.display_name} for {fetch_date.isoformat()}: {e}", file=sys.stderr)
            return 1

    return 0


def main():
    """Main entry point for the application."""
    try:
        parser = argparse.ArgumentParser(
            description="Comic Strip Browser - Browse and download comic strips",
            add_help=False
        )
        parser.add_argument("--names", action="store_true", help="Print all comic internal names")
        parser.add_argument("--info", action="store_true", help="Print full comic information list")
        parser.add_argument("--all", action="store_true", help="Download all available comics")
        parser.add_argument("--name", type=str, help="Download a comic by its internal name")
        parser.add_argument("--number", type=int, help="Download a comic by its 1-based index (1-80)")

        date_group = parser.add_mutually_exclusive_group()
        date_group.add_argument("--today", action="store_true", help="Target today's comic (default)")
        date_group.add_argument("--yesterday", action="store_true", help="Target yesterday's comic")

        parser.add_argument("--debug", action="store_true", help="Enable debug logging")
        parser.add_argument("--future", action="store_true", help="Allow future dates")
        parser.add_argument("-h", "--help", action="store_true", help="Show help message")

        args, _ = parser.parse_known_args()

        if args.help:
            _attach_console()
            parser.print_help()
            return 0

        # Check if any CLI action was requested
        is_cli_action = (
            args.names or args.info or args.all or
            args.name is not None or args.number is not None
        )

        import logging
        if args.debug:
            logging.basicConfig(
                filename='comic_browser.log',
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)
        else:
            logging.disable(logging.CRITICAL)

        if args.future:
            os.environ["COMIC_BROWSER_ALLOW_FUTURE"] = "1"

        if is_cli_action:
            return handle_cli(args)

        # Launch GUI application
        browser = ComicStripBrowser()
        return browser.run()
    except Exception as e:
        print(f"Error starting Comic Strip Browser: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

