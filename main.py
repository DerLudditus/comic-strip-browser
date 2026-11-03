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
from typing import Optional
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


def _check_debug_mode(cli_debug: bool = False) -> bool:
    """
    Check if debug mode is triggered by a debug.txt file or CLI argument.
    Looks for debug.txt in the application root, beside the executable, or in cache/.
    """
    if cli_debug:
        return True

    # 1. Current working directory
    if Path("debug.txt").is_file():
        return True

    # 2. cache/ folder
    if (Path("cache") / "debug.txt").is_file():
        return True

    # 3. Beside frozen executable or source file root
    try:
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            if (exe_dir / "debug.txt").is_file() or (exe_dir / "cache" / "debug.txt").is_file():
                return True
        else:
            root_dir = Path(__file__).resolve().parent
            if (root_dir / "debug.txt").is_file() or (root_dir / "cache" / "debug.txt").is_file():
                return True
    except Exception:
        pass

    return False


def _get_log_file_path() -> Path:
    """
    Return the log file path located inside the application cache directory (cache/comic_browser.log).
    This allows users to view the log directly by clicking 'Open Cache' in the GUI.
    """
    try:
        cache_dir = Path("cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "comic_browser.log"
    except Exception:
        # Fallback to current working directory
        return Path.cwd() / "comic_browser.log"


class ComicStripBrowser:
    """Main application class for the Comic Strip Browser."""
    
    def __init__(self, debug: bool = False, browser_preference: Optional[str] = None):
        """Initialize the comic strip browser application."""
        self.debug = debug
        self.browser_preference = browser_preference
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
            self.web_scraper = WebScraper(
                error_handler=self.error_handler,
                debug=self.debug,
                browser_preference=self.browser_preference,
            )
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
            self.main_window = MainWindow(
                browser_preference=self.browser_preference,
                debug=self.debug
            )

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


def handle_cli(args, debug: bool = False) -> int:
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
    browser_pref = "firefox" if getattr(args, "prefer_firefox", False) else (
        "chromium" if getattr(args, "prefer_chromium", False) else None
    )
    browser = ComicStripBrowser(debug=debug, browser_preference=browser_pref)
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


def _enforce_source_dependencies(is_gui: bool = True) -> None:
    """
    When running from source (not frozen fat binary), verifies that essential
    dependencies (specifically curl_cffi) are installed. If missing, refuses
    to run, prints diagnostic instructions, and displays a GUI dialog if applicable.
    """
    if getattr(sys, "frozen", False):
        return

    try:
        import curl_cffi  # noqa: F401
    except ImportError:
        msg = (
            "CRITICAL ERROR: Missing required dependency 'curl_cffi'.\n\n"
            "Comic Strip Browser requires 'curl_cffi' to provide authentic browser TLS "
            "fingerprints and bypass GoComics Bunny Shield security challenges.\n\n"
            "Standard 'requests' (urllib3) lacks TLS impersonation, causing GoComics "
            "to repeatedly block requests and trigger security challenges.\n\n"
            "To run the application from source, please install curl_cffi:\n\n"
            "  On Debian / Ubuntu / Linux:\n"
            "    python3 -m venv venv --system-site-packages\n"
            "    source venv/bin/activate\n"
            "    pip install curl_cffi\n"
            "    (or: pip install --break-system-packages curl_cffi)\n\n"
            "  On Windows:\n"
            "    pip install curl_cffi\n"
        )
        _attach_console()
        print(f"\n{'=' * 78}\n{msg}{'=' * 78}\n", file=sys.stderr)

        if is_gui:
            try:
                app = QApplication.instance()
                created = False
                if app is None:
                    app = QApplication(sys.argv)
                    created = True
                QMessageBox.critical(
                    None,
                    "Missing Required Dependency: curl_cffi",
                    msg,
                )
                if created:
                    app.quit()
            except Exception:
                pass
        sys.exit(1)


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

        browser_group = parser.add_mutually_exclusive_group()
        browser_group.add_argument("--prefer-firefox", action="store_true", help="Prefer Firefox (or Firefox ESR) for challenge resolution")
        browser_group.add_argument("--prefer-chromium", action="store_true", help="Prefer Chromium (or Edge/Chrome) for challenge resolution")

        date_group = parser.add_mutually_exclusive_group()
        date_group.add_argument("--today", action="store_true", help="Target today's comic (default)")
        date_group.add_argument("--yesterday", action="store_true", help="Target yesterday's comic")

        parser.add_argument("--debug", action="store_true", help="Enable debug logging")
        parser.add_argument("--future", action="store_true", help="Allow future dates")
        parser.add_argument("--fake429", action="store_true", help="Simulate GoComics 429 Too Many Requests response")
        parser.add_argument("--fake403", action="store_true", help="Simulate GoComics 403 Forbidden response")
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

        # Enforce curl_cffi dependency when running from source
        _enforce_source_dependencies(is_gui=not is_cli_action)

        import logging
        is_debug = _check_debug_mode(cli_debug=args.debug)
        if is_debug:
            _attach_console()
            log_file = _get_log_file_path()

            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)
            for handler in list(root_logger.handlers):
                root_logger.removeHandler(handler)

            formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')

            try:
                file_handler = logging.FileHandler(str(log_file), mode='w', encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception as e:
                print(f"[DEBUG] Could not open log file {log_file}: {e}", file=sys.stderr)

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

            print(f"[DEBUG] Debug logging enabled. Log file: {log_file}")
            logging.getLogger("main").debug(f"Comic Strip Browser v{__version__} starting with debug mode enabled")
        else:
            logging.disable(logging.CRITICAL)

        if args.future:
            os.environ["COMIC_BROWSER_ALLOW_FUTURE"] = "1"

        if args.fake429:
            os.environ["COMIC_BROWSER_FAKE_429"] = "1"

        if args.fake403:
            os.environ["COMIC_BROWSER_FAKE_403"] = "1"
            
        if is_cli_action:
            return handle_cli(args, debug=is_debug)

        # Launch GUI application
        browser_pref = "firefox" if args.prefer_firefox else ("chromium" if args.prefer_chromium else None)
        browser = ComicStripBrowser(debug=is_debug, browser_preference=browser_pref)
        return browser.run()
    except Exception as e:
        print(f"Error starting Comic Strip Browser: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

