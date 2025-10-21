"""
Core comic service layer for orchestrating comic retrieval workflow.

This module provides the ComicService class that coordinates between the
WebScraper, CacheManager, and ConfigManager to provide a unified interface
for comic retrieval with caching, fallback logic, and availability validation.
"""

# import logging
from datetime import date, timedelta
from typing import Optional, Dict, List

from models.data_models import ComicData, get_comic_definition, COMIC_DEFINITIONS
from services.web_scraper import WebScraper, WebScrapingError
from services.cache_manager import CacheManager
from services.config_manager import ConfigManager
from services.date_manager import DateManager
from services.error_handler import ErrorHandler, ComicUnavailableError, NetworkError, ParsingError, CacheError


class ComicServiceError(Exception):
    """Exception raised when comic service operations fail."""
    pass


class ComicService:
    """
    Core service for comic retrieval and management.
    
    This class orchestrates the comic retrieval workflow by coordinating
    between web scraping, caching, and configuration management. It provides
    fallback logic for failed requests and validates comic availability.
    """
    
    def __init__(self, 
                 web_scraper: Optional[WebScraper] = None,
                 cache_manager: Optional[CacheManager] = None,
                 config_manager: Optional[ConfigManager] = None,
                 date_manager: Optional[DateManager] = None,
                 error_handler: Optional[ErrorHandler] = None):
        """
        Initialize the ComicService with its dependencies.
        
        Args:
            web_scraper: WebScraper instance for fetching comics
            cache_manager: CacheManager instance for local storage
            config_manager: ConfigManager instance for configuration
            date_manager: DateManager instance for date discovery
            error_handler: ErrorHandler instance for error management
        """
        self.error_handler = error_handler or ErrorHandler()
        self.web_scraper = web_scraper or WebScraper(error_handler=self.error_handler)
        self.cache_manager = cache_manager or CacheManager(error_handler=self.error_handler)
        self.config_manager = config_manager or ConfigManager()
        self.date_manager = date_manager or DateManager(
            web_scraper=self.web_scraper,
            config_manager=self.config_manager
        )
        # self.logger = logging.getLogger(__name__)
    
    def get_comic(self, comic_name: str, comic_date: Optional[date] = None) -> ComicData:
        """
        Retrieve a comic for a specific date with fallback logic.
        
        This method implements the core comic retrieval workflow:
        1. Use current date if no date specified
        2. Check cache first
        3. If not cached, fetch from web
        4. If current day fails, try yesterday
        5. Cache successful results
        
        Args:
            comic_name: Name of the comic strip
            comic_date: Date to retrieve (defaults to today)
            
        Returns:
            ComicData object with comic information
            
        Raises:
            ComicServiceError: If comic cannot be retrieved
        """
        # Use current date if none specified
        if comic_date is None:
            comic_date = date.today()
        
        # Validate comic name
        comic_def = get_comic_definition(comic_name)
        if not comic_def:
            raise ComicServiceError(f"Unknown comic: {comic_name}")
        
        # Validate date availability (but allow some flexibility for older dates)
        # if not self.validate_comic_availability(comic_name, comic_date):
        #    self.logger.warning(f"Comic {comic_name} may not be available for {comic_date}, but will attempt retrieval")
        
        # self.logger.info(f"Retrieving comic {comic_name} for {comic_date}")
        
        # Try to get from cache first
        cached_comic = self.cache_manager.get_cached_comic(comic_name, comic_date)
        if cached_comic:
            # self.logger.info(f"Found cached comic {comic_name} for {comic_date}")
            return cached_comic
        
        # Not in cache, try to fetch from web
        try:
            comic_data = self._fetch_comic_from_web(comic_name, comic_date)
            
            # Cache the successful result
            try:
                # if 
                self.cache_manager.cache_comic(comic_data)
                #    self.logger.info(f"Cached comic {comic_name} for {comic_date}")
                # else:
                #    self.logger.warning(f"Failed to cache comic {comic_name} for {comic_date}")
            except Exception as cache_error:
                # Cache errors are non-fatal, just log them
                self.error_handler.handle_cache_error(cache_error, "save", comic_name, comic_date)
            
            return comic_data
            
        except ComicUnavailableError:
            # Comic not available for this date, try fallback if it's today
            if comic_date == date.today():
                yesterday = comic_date - timedelta(days=1)
                # self.logger.info(f"Trying yesterday's comic ({yesterday}) as fallback")
                
                try:
                    return self.get_comic(comic_name, yesterday)
                except (ComicServiceError, ComicUnavailableError):
                    pass  # Fall through to main error
            
            # Re-raise the ComicUnavailableError
            raise ComicServiceError(f"Comic {comic_name} not available for {comic_date}")
            
        except (NetworkError, ParsingError) as e:
            # Try to get from cache as fallback for network/parsing errors
            cached_comic = self.cache_manager.get_cached_comic(comic_name, comic_date)
            if cached_comic:
                # self.logger.info(f"Using cached comic as fallback for {comic_name} on {comic_date}")
                return cached_comic
            
            # If requesting today's comic and it failed, try yesterday
            if comic_date == date.today():
                yesterday = comic_date - timedelta(days=1)
                # self.logger.info(f"Trying yesterday's comic ({yesterday}) as fallback")
                
                try:
                    return self.get_comic(comic_name, yesterday)
                except ComicServiceError:
                    pass  # Fall through to main error
            
            raise ComicServiceError(f"Could not retrieve {comic_name} for {comic_date}: {e}")
            
        except WebScrapingError as e:
            # self.logger.warning(f"Failed to fetch {comic_name} for {comic_date}: {e}")
            
            # If requesting today's comic and it failed, try yesterday
            if comic_date == date.today():
                yesterday = comic_date - timedelta(days=1)
                # self.logger.info(f"Trying yesterday's comic ({yesterday}) as fallback")
                
                try:
                    return self.get_comic(comic_name, yesterday)
                except ComicServiceError:
                    pass  # Fall through to main error
            
            raise ComicServiceError(f"Could not retrieve {comic_name} for {comic_date}: {e}")
    
    def _fetch_comic_from_web(self, comic_name: str, comic_date: date) -> ComicData:
        """
        Fetch comic data from the web.
        
        Args:
            comic_name: Name of the comic strip
            comic_date: Date to retrieve
            
        Returns:
            ComicData object with comic information
            
        Raises:
            WebScrapingError: If comic cannot be fetched
        """
        comic_def = get_comic_definition(comic_name)
        if not comic_def:
            raise WebScrapingError(f"Unknown comic: {comic_name}")
        
        return self.web_scraper.get_comic_data(comic_name, comic_def.base_url, comic_date)
    
    def validate_comic_availability(self, comic_name: str, comic_date: date) -> bool:
        """
        Validate if a comic is available for a specific date.
        
        Args:
            comic_name: Name of the comic strip
            comic_date: Date to check
            
        Returns:
            True if comic should be available, False otherwise
        """
        # Check if comic name is valid
        comic_def = get_comic_definition(comic_name)
        if not comic_def:
            return False
        
        # Check if date is not in the future
        if comic_date > date.today():
            return False
        
        # Check against known start date if available
        start_date = self.config_manager.get_start_date(comic_name)
        if start_date and comic_date < start_date:
            return False
        
        return True
    
    def discover_earliest_dates(self, progress_callback=None) -> Dict[str, date]:
        """
        Discover the earliest available dates for all comics with progress reporting.
        
        This method uses the DateManager to find the earliest available
        date for each comic strip and saves the results to configuration.
        Uses optimized discovery and allows partial results.
        
        Args:
            progress_callback: Optional callback function for progress updates
        
        Returns:
            Dictionary mapping comic names to their earliest dates
            
        Raises:
            ComicServiceError: If date discovery fails completely
        """
        try:
            # self.logger.info("Starting optimized earliest date discovery for all comics")
            
            if progress_callback:
                progress_callback("Starting date discovery for all comics...", 0)
            
            earliest_dates = {}
            total_comics = len(COMIC_DEFINITIONS)
            
            for i, comic_def in enumerate(COMIC_DEFINITIONS):
                # self.logger.info(f"Discovering earliest date for {comic_def.name} ({i+1}/{total_comics})")
                
                if progress_callback:
                    progress = int((i / total_comics) * 100)
                    progress_callback(f"Discovering dates for {comic_def.display_name}...", progress)
                
                try:
                    # Use optimized discovery with progress callback
                    def comic_progress(msg):
                        if progress_callback:
                            progress_callback(f"{comic_def.display_name}: {msg}", progress)
                    
                    earliest_date = self.date_manager.discover_earliest_date(comic_def.name, comic_progress)
                    if earliest_date is not None:
                        earliest_dates[comic_def.name] = earliest_date
                        # self.logger.info(f"Found earliest date for {comic_def.name}: {earliest_date}")
                        
                        # Save partial results as we go
                        self.config_manager.set_start_date(comic_def.name, earliest_date)
                    # else:
                       # self.logger.warning(f"No earliest date found for {comic_def.name}")
                    
                except Exception as e:
                    # self.logger.error(f"Failed to discover earliest date for {comic_def.name}: {e}")
                    # Continue with other comics even if one fails
                    continue
            
            if progress_callback:
                progress_callback("Date discovery completed!", 100)
            
            # Save all discovered dates to configuration
            if earliest_dates:
                self.config_manager.save_start_dates(earliest_dates)
                # self.logger.info(f"Saved {len(earliest_dates)} earliest dates to configuration")
            
            return earliest_dates
            
        except Exception as e:
            # self.logger.error(f"Date discovery failed: {e}")
            raise ComicServiceError(f"Failed to discover earliest dates: {e}")
    
    def get_available_comics(self) -> List[Dict[str, str]]:
        """
        Get list of all available comics with their metadata.
        
        Returns:
            List of dictionaries containing comic information
        """
        comics = []
        for comic_def in COMIC_DEFINITIONS:
            start_date = self.config_manager.get_start_date(comic_def.name)
            
            comic_info = {
                'name': comic_def.name,
                'display_name': comic_def.display_name,
                'author': comic_def.author,
                'base_url': comic_def.base_url,
                'earliest_date': start_date.isoformat() if start_date else None
            }
            comics.append(comic_info)
        
        return comics
    
    def is_comic_cached(self, comic_name: str, comic_date: date) -> bool:
        """
        Check if a comic is available in cache.
        
        Args:
            comic_name: Name of the comic strip
            comic_date: Date to check
            
        Returns:
            True if comic is cached, False otherwise
        """
        return self.cache_manager.is_cached(comic_name, comic_date)
    
    def get_cached_dates(self, comic_name: str) -> List[date]:
        """
        Get list of cached dates for a specific comic.
        
        Args:
            comic_name: Name of the comic strip
            
        Returns:
            List of dates that are cached for this comic
        """
        return self.cache_manager.get_cached_dates(comic_name)
    
    def get_cache_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get cache statistics for all comics.
        
        Returns:
            Dictionary mapping comic names to their cache statistics
        """
        return self.cache_manager.get_all_cache_stats()
    
    def clear_cache(self, comic_name: Optional[str] = None) -> None:
        """
        Clear cache for a specific comic or all comics.
        
        Args:
            comic_name: Name of comic to clear, or None to clear all
        """
        self.cache_manager.clear_cache(comic_name)
        # self.logger.info(f"Cleared cache for {comic_name or 'all comics'}")
    
    def initialize_if_needed(self) -> bool:
        """
        Initialize the service by discovering earliest dates if not already done.
        
        This method checks if all comic start dates are available in the
        configuration. If not, it triggers the date discovery process.
        
        Returns:
            True if initialization was needed and completed, False if already initialized
            
        Raises:
            ComicServiceError: If initialization fails
        """
        if self.config_manager.has_all_start_dates():
            # self.logger.info("All start dates already available, skipping initialization")
            return False
        
        self.logger.info("Start dates missing, beginning initialization")
        
        try:
            discovered_dates = self.discover_earliest_dates()
            
            if len(discovered_dates) < len(COMIC_DEFINITIONS):
                missing_comics = set(comic_def.name for comic_def in COMIC_DEFINITIONS) - set(discovered_dates.keys())
                # self.logger.warning(f"Could not discover dates for: {missing_comics}")
            
            # self.logger.info("Service initialization completed")
            return True
            
        except Exception as e:
            # self.logger.error(f"Service initialization failed: {e}")
            raise ComicServiceError(f"Failed to initialize service: {e}")
    
    def get_error_statistics(self) -> Dict[str, any]:
        """
        Get error statistics for monitoring and debugging.
        
        Returns:
            Dictionary with error statistics
        """
        return self.error_handler.get_error_statistics()
    
    def clear_error_statistics(self) -> None:
        """Clear error statistics and recent errors."""
        self.error_handler.clear_error_statistics()
    
    def get_user_friendly_error_message(self, error: Exception) -> str:
        """
        Get a user-friendly error message for an exception.
        
        Args:
            error: The exception to get a message for
            
        Returns:
            User-friendly error message
        """
        # Convert ComicServiceError to appropriate error type for user message
        if isinstance(error, ComicServiceError):
            error_msg = str(error).lower()
            if "not available" in error_msg:
                # Try to extract comic name and date from the original error message
                original_msg = str(error)
                
                # Parse the original message: "Comic wumo not available for 2013-10-14"
                import re
                from datetime import datetime
                
                # Extract comic name and date
                comic_name = "unknown"
                error_date = date.today()
                
                # Try to parse: "Comic COMIC_NAME not available for YYYY-MM-DD"
                match = re.search(r'Comic (\w+) not available for (\d{4}-\d{2}-\d{2})', original_msg)
                if match:
                    comic_name = match.group(1)
                    try:
                        error_date = datetime.strptime(match.group(2), '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                # Create a ComicUnavailableError with correct info
                from services.error_handler import ComicUnavailableError
                comic_error = ComicUnavailableError(str(error), comic_name, error_date)
                return self.error_handler.get_user_friendly_message(comic_error)
            elif "network" in error_msg or "connection" in error_msg:
                from services.error_handler import NetworkError
                network_error = NetworkError(str(error))
                return self.error_handler.get_user_friendly_message(network_error)
            else:
                from services.error_handler import ComicError, ErrorType, ErrorSeverity
                comic_error = ComicError(str(error), ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM)
                return self.error_handler.get_user_friendly_message(comic_error)
        
        # Handle ErrorHandler exceptions directly
        if hasattr(error, 'error_type'):
            return self.error_handler.get_user_friendly_message(error)
        
        # Default fallback message
        return "An unexpected error occurred. Please try again."
    
    def get_recovery_suggestions(self, error: Exception) -> List[str]:
        """
        Get recovery suggestions for an exception.
        
        Args:
            error: The exception to get suggestions for
            
        Returns:
            List of recovery suggestions
        """
        # Convert ComicServiceError to appropriate error type for suggestions
        if isinstance(error, ComicServiceError):
            error_msg = str(error).lower()
            if "not available" in error_msg:
                from services.error_handler import ComicUnavailableError
                comic_error = ComicUnavailableError(str(error), "unknown", date.today())
                return self.error_handler.get_recovery_suggestions(comic_error)
            elif "network" in error_msg or "connection" in error_msg:
                from services.error_handler import NetworkError
                network_error = NetworkError(str(error))
                return self.error_handler.get_recovery_suggestions(network_error)
        
        # Handle ErrorHandler exceptions directly
        if hasattr(error, 'error_type'):
            return self.error_handler.get_recovery_suggestions(error)
        
        # Default fallback suggestions
        return ["Try again later", "Check your internet connection", "Contact support if the problem persists"]