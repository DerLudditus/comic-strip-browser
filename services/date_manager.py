"""
Date discovery service for finding earliest available comic dates.

This module provides the DateManager class that implements a binary search
algorithm to discover the earliest available date for each comic strip,
using a year-by-year approach followed by month-by-month refinement.
"""

import logging
from datetime import date, timedelta
from typing import Dict, Optional, Tuple
from services.web_scraper import WebScraper, WebScrapingError
from services.config_manager import ConfigManager
from models.data_models import COMIC_DEFINITIONS, get_comic_definition


class DateDiscoveryError(Exception):
    """Exception raised when date discovery fails."""
    pass


class DateManager:
    """
    Manages date discovery for comic strips using binary search algorithm.
    
    This class implements a two-phase discovery process:
    1. Go back 1 year at a time until failure is detected
    2. Refine by months to find the exact earliest date
    """
    
    def __init__(self, web_scraper: Optional[WebScraper] = None, 
                 config_manager: Optional[ConfigManager] = None):
        """
        Initialize the DateManager.
        
        Args:
            web_scraper: WebScraper instance for fetching comic pages
            config_manager: ConfigManager instance for storing results
        """
        self.web_scraper = web_scraper or WebScraper()
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)
        
    def discover_earliest_date(self, comic_name: str, progress_callback=None) -> Optional[date]:
        """
        Discover the earliest available date for a specific comic.
        
        Uses optimized binary search algorithm:
        1. Start with reasonable estimates based on comic age
        2. Go back in larger steps initially, then refine
        3. Use timeout to prevent hanging
        
        Args:
            comic_name: Name of the comic strip
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Earliest available date, or None if discovery fails
            
        Raises:
            DateDiscoveryError: If comic definition is not found or discovery fails
        """
        comic_def = get_comic_definition(comic_name)
        if not comic_def:
            raise DateDiscoveryError(f"Comic definition not found for: {comic_name}")
        
        self.logger.info(f"Starting optimized date discovery for {comic_name}")
        
        if progress_callback:
            progress_callback(f"Discovering dates for {comic_name}...")
        
        try:
            # Use optimized discovery with reasonable starting points
            earliest_date = self._optimized_discovery(comic_def.name, comic_def.base_url, progress_callback)
            
            if earliest_date:
                self.logger.info(f"Discovered earliest date for {comic_name}: {earliest_date}")
                return earliest_date
            else:
                self.logger.warning(f"Could not find earliest date for {comic_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Date discovery failed for {comic_name}: {e}")
            # Don't raise exception, just return None to allow partial discovery
            return None
    
    def _find_earliest_year(self, comic_name: str, base_url: str) -> Optional[int]:
        """
        Find the earliest year with available comics using yearly steps.
        
        Args:
            comic_name: Name of the comic strip
            base_url: Base URL for the comic
            
        Returns:
            Earliest year with comics, or None if not found
        """
        current_year = date.today().year
        test_date = date(current_year, 1, 1)  # Start with January 1st of current year
        
        # First, verify current year has comics
        if not self._test_comic_availability(comic_name, base_url, test_date):
            self.logger.warning(f"No comics found for {comic_name} in current year {current_year}")
            return None
        
        last_working_year = current_year
        
        # Go back year by year until we find failure
        for years_back in range(1, 100):  # Reasonable limit to prevent infinite loops
            test_year = current_year - years_back
            test_date = date(test_year, 1, 1)
            
            self.logger.debug(f"Testing year {test_year} for {comic_name}")
            
            if self._test_comic_availability(comic_name, base_url, test_date):
                last_working_year = test_year
            else:
                # Found the boundary - comics don't exist in this year
                self.logger.debug(f"Comics not available in {test_year} for {comic_name}")
                break
        
        return last_working_year
    
    def _refine_by_months(self, comic_name: str, base_url: str, year: int) -> Optional[date]:
        """
        Refine the earliest date by testing months within the given year.
        
        Args:
            comic_name: Name of the comic strip
            base_url: Base URL for the comic
            year: Year to search within
            
        Returns:
            Earliest available date, or None if not found
        """
        self.logger.debug(f"Refining earliest date by months for {comic_name} in {year}")
        
        # Test each month from January to December
        for month in range(1, 13):
            # Try the first day of each month
            test_date = date(year, month, 1)
            
            if self._test_comic_availability(comic_name, base_url, test_date):
                # Found a working month, now refine by days
                earliest_in_month = self._refine_by_days(comic_name, base_url, year, month)
                if earliest_in_month:
                    return earliest_in_month
        
        # If no month worked, try the previous year's December
        if year > 1900:  # Reasonable lower bound
            prev_year_date = date(year - 1, 12, 31)
            if self._test_comic_availability(comic_name, base_url, prev_year_date):
                return self._refine_by_days(comic_name, base_url, year - 1, 12)
        
        return None
    
    def _refine_by_days(self, comic_name: str, base_url: str, year: int, month: int) -> Optional[date]:
        """
        Refine the earliest date by testing days within the given month.
        
        Args:
            comic_name: Name of the comic strip
            base_url: Base URL for the comic
            year: Year to search within
            month: Month to search within
            
        Returns:
            Earliest available date in the month, or None if not found
        """
        self.logger.debug(f"Refining earliest date by days for {comic_name} in {year}-{month:02d}")
        
        # Get the number of days in the month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        
        last_day_of_month = (next_month - timedelta(days=1)).day
        
        # Test each day from 1st to last day of month
        for day in range(1, last_day_of_month + 1):
            test_date = date(year, month, day)
            
            if self._test_comic_availability(comic_name, base_url, test_date):
                self.logger.debug(f"Found earliest date for {comic_name}: {test_date}")
                return test_date
        
        return None
    
    def _optimized_discovery(self, comic_name: str, base_url: str, progress_callback=None) -> Optional[date]:
        """
        Optimized discovery algorithm that uses smarter starting points and fewer requests.
        
        Args:
            comic_name: Name of the comic strip
            base_url: Base URL for the comic
            progress_callback: Optional callback for progress updates
            
        Returns:
            Earliest available date, or None if not found
        """
        # Smart starting points based on known comic history
        comic_start_estimates = {
            'garfield': 1978,
            'peanuts': 1950,
            'calvinandhobbes': 1985,
            'pearlsbeforeswine': 2002,
            'wizardofid': 1964,
            'bc': 1958,
            'pickles': 1990,
            'shoe': 1977,
            'wumo': 2005,
            'speedbump': 1994,
            'freerange': 2006,
        }
        
        # Get estimated start year or use conservative default
        estimated_start = comic_start_estimates.get(comic_name, 1990)
        current_year = date.today().year
        
        if progress_callback:
            progress_callback(f"Checking {comic_name} from ~{estimated_start}...")
        
        # Phase 1: Quick verification - test estimated year first
        test_date = date(estimated_start, 1, 1)
        if self._test_comic_availability(comic_name, base_url, test_date):
            # Great! Our estimate was good, now refine backwards
            earliest_year = self._binary_search_year(comic_name, base_url, estimated_start - 10, estimated_start)
        else:
            # Estimate was too early, search forward
            earliest_year = self._binary_search_year(comic_name, base_url, estimated_start, current_year)
        
        if earliest_year is None:
            return None
        
        if progress_callback:
            progress_callback(f"Found {comic_name} starts in {earliest_year}, refining...")
        
        # Phase 2: Refine by months (but only test a few key dates)
        return self._quick_refine_by_months(comic_name, base_url, earliest_year)
    
    def _binary_search_year(self, comic_name: str, base_url: str, start_year: int, end_year: int) -> Optional[int]:
        """
        Use binary search to find the earliest year more efficiently.
        
        Args:
            comic_name: Name of the comic strip
            base_url: Base URL for the comic
            start_year: Starting year for search
            end_year: Ending year for search
            
        Returns:
            Earliest year with comics, or None if not found
        """
        if start_year > end_year:
            return None
        
        # Limit search to reasonable bounds
        start_year = max(start_year, 1900)
        end_year = min(end_year, date.today().year)
        
        earliest_found = None
        
        while start_year <= end_year:
            mid_year = (start_year + end_year) // 2
            test_date = date(mid_year, 6, 15)  # Test mid-year date
            
            if self._test_comic_availability(comic_name, base_url, test_date):
                earliest_found = mid_year
                end_year = mid_year - 1  # Search earlier
            else:
                start_year = mid_year + 1  # Search later
        
        return earliest_found
    
    def _quick_refine_by_months(self, comic_name: str, base_url: str, year: int) -> Optional[date]:
        """
        Quick refinement by testing only a few key dates per month.
        
        Args:
            comic_name: Name of the comic strip
            base_url: Base URL for the comic
            year: Year to search within
            
        Returns:
            Earliest available date, or None if not found
        """
        # Test key dates: 1st, 15th of each month
        for month in range(1, 13):
            for day in [1, 15]:
                try:
                    test_date = date(year, month, day)
                    if self._test_comic_availability(comic_name, base_url, test_date):
                        # Found a working date, now do precise day search in this month
                        return self._refine_by_days(comic_name, base_url, year, month)
                except ValueError:
                    # Invalid date (e.g., Feb 30), skip
                    continue
        
        return None

    def _test_comic_availability(self, comic_name: str, base_url: str, test_date: date) -> bool:
        """
        Test if a comic is available for a specific date.
        
        Args:
            comic_name: Name of the comic strip
            base_url: Base URL for the comic
            test_date: Date to test
            
        Returns:
            True if comic is available, False otherwise
        """
        try:
            # Attempt to retrieve comic data for the test date
            comic_data = self.web_scraper.get_comic_data(comic_name, base_url, test_date)
            
            # If we got valid comic data, the date is available
            return comic_data is not None and bool(comic_data.image_url)
            
        except WebScrapingError as e:
            # Check if it's a 404 error or missing comic data
            if "404" in str(e) or "not found" in str(e).lower():
                self.logger.debug(f"Comic not available for {comic_name} on {test_date}: 404")
                return False
            elif "empty" in str(e).lower() or "missing" in str(e).lower():
                self.logger.debug(f"Comic data missing for {comic_name} on {test_date}")
                return False
            else:
                # Other errors might be temporary, so we'll consider them as unavailable
                self.logger.debug(f"Error testing {comic_name} on {test_date}: {e}")
                return False
        except Exception as e:
            # Any other exception means the comic is not available
            self.logger.debug(f"Unexpected error testing {comic_name} on {test_date}: {e}")
            return False
    
    def discover_all_earliest_dates(self) -> Dict[str, date]:
        """
        Discover earliest dates for all 15 comic strips.
        
        Returns:
            Dictionary mapping comic names to their earliest dates
            
        Raises:
            DateDiscoveryError: If discovery fails for any comic
        """
        self.logger.info("Starting discovery of earliest dates for all comics")
        
        earliest_dates = {}
        failed_comics = []
        
        for comic_def in COMIC_DEFINITIONS:
            try:
                earliest_date = self.discover_earliest_date(comic_def.name)
                if earliest_date:
                    earliest_dates[comic_def.name] = earliest_date
                else:
                    failed_comics.append(comic_def.name)
                    self.logger.warning(f"Failed to discover earliest date for {comic_def.name}")
            except Exception as e:
                failed_comics.append(comic_def.name)
                self.logger.error(f"Error discovering earliest date for {comic_def.name}: {e}")
        
        if failed_comics:
            self.logger.warning(f"Failed to discover dates for comics: {failed_comics}")
        
        self.logger.info(f"Successfully discovered earliest dates for {len(earliest_dates)} comics")
        return earliest_dates
    
    def run_discovery_and_save(self) -> bool:
        """
        Run the one-time discovery process and save results to config.
        
        This method checks if all start dates are already available in config.
        If not, it runs the discovery process and saves the results.
        
        Returns:
            True if discovery was successful or not needed, False otherwise
        """
        # Check if we already have all start dates
        if self.config_manager.has_all_start_dates():
            self.logger.info("All start dates already available in config, skipping discovery")
            return True
        
        self.logger.info("Running one-time date discovery process")
        
        try:
            # Discover earliest dates for all comics
            earliest_dates = self.discover_all_earliest_dates()
            
            if not earliest_dates:
                self.logger.error("No earliest dates discovered")
                return False
            
            # Save the discovered dates to config
            self.config_manager.save_start_dates(earliest_dates)
            
            self.logger.info(f"Successfully saved earliest dates for {len(earliest_dates)} comics")
            return True
            
        except Exception as e:
            self.logger.error(f"Date discovery and save process failed: {e}")
            return False
    
    def get_earliest_date(self, comic_name: str) -> Optional[date]:
        """
        Get the earliest date for a comic, running discovery if needed.
        
        Args:
            comic_name: Name of the comic strip
            
        Returns:
            Earliest available date, or None if not available
        """
        # First try to get from config
        earliest_date = self.config_manager.get_start_date(comic_name)
        
        if earliest_date is not None:
            return earliest_date
        
        # If not in config, try to discover it
        try:
            discovered_date = self.discover_earliest_date(comic_name)
            if discovered_date:
                # Save the discovered date
                self.config_manager.set_start_date(comic_name, discovered_date)
                return discovered_date
        except Exception as e:
            self.logger.error(f"Failed to discover earliest date for {comic_name}: {e}")
        
        return None
    
    def is_date_available(self, comic_name: str, check_date: date) -> bool:
        """
        Check if a specific date is available for a comic.
        
        Args:
            comic_name: Name of the comic strip
            check_date: Date to check
            
        Returns:
            True if the date is available, False otherwise
        """
        earliest_date = self.get_earliest_date(comic_name)
        
        if earliest_date is None:
            # If we don't know the earliest date, test directly
            comic_def = get_comic_definition(comic_name)
            if comic_def:
                return self._test_comic_availability(comic_name, comic_def.base_url, check_date)
            return False
        
        # Check if the requested date is on or after the earliest date
        return check_date >= earliest_date
