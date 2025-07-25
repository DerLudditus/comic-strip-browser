"""
Error handling system for the comic strip browser application.

This module provides comprehensive error handling with specific recovery strategies
for network errors, parsing errors, and cache errors. It implements retry logic
with exponential backoff and fallback mechanisms to ensure the application
continues to work even when some comics are unavailable.
"""

import time
import logging
from typing import Optional, Callable, Any, Dict, List, Type
from datetime import date, timedelta
from enum import Enum
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout, HTTPError

from models.data_models import ComicData


class ErrorType(Enum):
    """Types of errors that can occur in the application."""
    NETWORK_ERROR = "network"
    PARSING_ERROR = "parsing"
    CACHE_ERROR = "cache"
    COMIC_UNAVAILABLE = "comic_unavailable"
    UNKNOWN_ERROR = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComicError(Exception):
    """Base exception for comic-related errors."""
    
    def __init__(self, message: str, error_type: ErrorType, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.timestamp = time.time()


class NetworkError(ComicError):
    """Exception for network-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(message, ErrorType.NETWORK_ERROR, severity)
        self.status_code = status_code


class ParsingError(ComicError):
    """Exception for HTML parsing errors."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(message, ErrorType.PARSING_ERROR, severity)


class CacheError(ComicError):
    """Exception for cache-related errors."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.LOW):
        super().__init__(message, ErrorType.CACHE_ERROR, severity)


class ComicUnavailableError(ComicError):
    """Exception when a comic is not available."""
    
    def __init__(self, message: str, comic_name: str, comic_date: date):
        super().__init__(message, ErrorType.COMIC_UNAVAILABLE, ErrorSeverity.LOW)
        self.comic_name = comic_name
        self.comic_date = comic_date


class ErrorHandler:
    """
    Comprehensive error handling system with recovery strategies.
    
    This class provides centralized error handling for the comic strip browser
    application, including retry logic with exponential backoff, fallback
    mechanisms, and specific recovery strategies for different error types.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Initialize the error handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay in seconds between retries
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.logger = logging.getLogger(__name__)
        
        # Track error statistics
        self.error_counts: Dict[ErrorType, int] = {error_type: 0 for error_type in ErrorType}
        self.recent_errors: List[ComicError] = []
        self.max_recent_errors = 100
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    def _log_error(self, error: ComicError) -> None:
        """
        Log an error and update statistics.
        
        Args:
            error: The error to log
        """
        # Update error counts
        self.error_counts[error.error_type] += 1
        
        # Add to recent errors list
        self.recent_errors.append(error)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)
        
        # Log based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"{error.error_type.value}: {error}")
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"{error.error_type.value}: {error}")
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"{error.error_type.value}: {error}")
        else:
            self.logger.info(f"{error.error_type.value}: {error}")
    
    def retry_with_backoff(self, 
                          func: Callable[..., Any], 
                          *args, 
                          **kwargs) -> Any:
        """
        Execute a function with retry logic and exponential backoff.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            The last exception encountered if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.logger.info(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed: {e}")
        
        raise last_exception
    
    def handle_network_error(self, 
                           error: Exception, 
                           url: str, 
                           comic_name: str, 
                           comic_date: date) -> Optional[ComicData]:
        """
        Handle network-related errors with specific recovery strategies.
        
        Args:
            error: The original network error
            url: URL that failed
            comic_name: Name of the comic
            comic_date: Date of the comic
            
        Returns:
            ComicData if recovery successful, None otherwise
            
        Raises:
            NetworkError: If recovery fails
        """
        status_code = None
        severity = ErrorSeverity.MEDIUM
        
        if isinstance(error, HTTPError):
            status_code = error.response.status_code if error.response else None
            
            if status_code == 404:
                # Comic not found - this is expected for some dates
                severity = ErrorSeverity.LOW
                network_error = NetworkError(
                    f"Comic not found: {comic_name} for {comic_date} (404)",
                    status_code=404,
                    severity=severity
                )
                self._log_error(network_error)
                raise ComicUnavailableError(
                    f"Comic {comic_name} not available for {comic_date}",
                    comic_name,
                    comic_date
                )
            elif status_code >= 500:
                # Server error - might be temporary
                severity = ErrorSeverity.HIGH
        elif isinstance(error, (ConnectionError, Timeout)):
            # Connection issues - might be temporary
            severity = ErrorSeverity.HIGH
        
        network_error = NetworkError(
            f"Network error for {url}: {error}",
            status_code=status_code,
            severity=severity
        )
        self._log_error(network_error)
        
        # For high severity errors, we might want to try cache fallback
        if severity == ErrorSeverity.HIGH:
            self.logger.info(f"Network error occurred, caller should try cache fallback")
        
        raise network_error
    
    def handle_parsing_error(self, 
                           error: Exception, 
                           html_content: str, 
                           comic_name: str, 
                           comic_date: date) -> Optional[ComicData]:
        """
        Handle HTML parsing errors with fallback mechanisms.
        
        Args:
            error: The original parsing error
            html_content: HTML content that failed to parse
            comic_name: Name of the comic
            comic_date: Date of the comic
            
        Returns:
            ComicData if fallback parsing successful, None otherwise
            
        Raises:
            ParsingError: If all parsing attempts fail
        """
        parsing_error = ParsingError(
            f"Failed to parse comic data for {comic_name} on {comic_date}: {error}"
        )
        self._log_error(parsing_error)
        
        # Try fallback parsing strategies
        fallback_result = self._try_fallback_parsing(html_content, comic_name, comic_date)
        if fallback_result:
            self.logger.info(f"Fallback parsing successful for {comic_name} on {comic_date}")
            return fallback_result
        
        raise parsing_error
    
    def _try_fallback_parsing(self, 
                            html_content: str, 
                            comic_name: str, 
                            comic_date: date) -> Optional[ComicData]:
        """
        Attempt fallback parsing strategies.
        
        Args:
            html_content: HTML content to parse
            comic_name: Name of the comic
            comic_date: Date of the comic
            
        Returns:
            ComicData if successful, None otherwise
        """
        from bs4 import BeautifulSoup
        import re
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Fallback strategy 1: Look for any img tag with comic-related attributes
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src', '')
                alt = img.get('alt', '').lower()
                
                # Check if this looks like a comic image
                if any(keyword in src.lower() for keyword in ['comic', 'strip', 'feature']):
                    # Try to extract basic information
                    title = soup.find('title')
                    title_text = title.get_text().strip() if title else f"{comic_name} - {comic_date}"
                    
                    # Get image dimensions if available
                    width = 900  # Default width
                    height = 300  # Default height
                    
                    width_attr = img.get('width')
                    height_attr = img.get('height')
                    
                    if width_attr:
                        try:
                            width = int(width_attr)
                        except ValueError:
                            pass
                    
                    if height_attr:
                        try:
                            height = int(height_attr)
                        except ValueError:
                            pass
                    
                    # Determine image format from URL
                    image_format = 'jpeg'
                    if src.lower().endswith('.png'):
                        image_format = 'png'
                    elif src.lower().endswith('.gif'):
                        image_format = 'gif'
                    
                    # Get author from default mapping
                    author_mapping = {
                        'calvinandhobbes': 'Bill Watterson',
                        'peanuts': 'Charles M. Schulz',
                        'peanuts-begins': 'Charles M. Schulz',
                        'garfield': 'Jim Davis',
                        'wizardofid': 'Brant Parker and Johnny Hart',
                        'wizard-of-id-classics': 'Brant Parker and Johnny Hart',
                        'pearlsbeforeswine': 'Stephan Pastis',
                        'shoe': 'Jeff MacNelly',
                        'bc': 'Johnny Hart',
                        'back-to-bc': 'Johnny Hart',
                        'pickles': 'Brian Crane',
                        'wumo': 'Mikael Wulff and Anders Morgenthaler',
                        'speedbump': 'Dave Coverly',
                        'freerange': 'Bill Whitehead'
                    }
                    
                    author = author_mapping.get(comic_name, 'Unknown Author')
                    
                    return ComicData(
                        comic_name=comic_name,
                        date=comic_date,
                        title=title_text,
                        image_url=src,
                        image_width=width,
                        image_height=height,
                        image_format=image_format,
                        author=author
                    )
            
            # Fallback strategy 2: Look for JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'image' in data:
                        # This might contain comic information
                        pass  # Could implement JSON-LD parsing here
                except (json.JSONDecodeError, AttributeError):
                    continue
            
        except Exception as e:
            self.logger.debug(f"Fallback parsing failed: {e}")
        
        return None
    
    def handle_cache_error(self, 
                         error: Exception, 
                         operation: str, 
                         comic_name: str, 
                         comic_date: Optional[date] = None) -> None:
        """
        Handle cache-related errors with cleanup and fallback strategies.
        
        Args:
            error: The original cache error
            operation: Description of the cache operation that failed
            comic_name: Name of the comic
            comic_date: Date of the comic (if applicable)
        """
        cache_error = CacheError(
            f"Cache {operation} failed for {comic_name}" + 
            (f" on {comic_date}" if comic_date else "") + 
            f": {error}"
        )
        self._log_error(cache_error)
        
        # Cache errors are generally non-fatal, so we just log them
        # The application should continue without caching
        self.logger.info(f"Continuing without cache for {operation}")
    
    def handle_comic_unavailable(self, 
                               comic_name: str, 
                               comic_date: date, 
                               try_previous_day: bool = True) -> Optional[ComicData]:
        """
        Handle comic unavailable errors with fallback to previous day.
        
        Args:
            comic_name: Name of the comic
            comic_date: Date that was unavailable
            try_previous_day: Whether to try the previous day as fallback
            
        Returns:
            ComicData if fallback successful, None otherwise
            
        Raises:
            ComicUnavailableError: If no fallback options work
        """
        error = ComicUnavailableError(
            f"Comic {comic_name} not available for {comic_date}",
            comic_name,
            comic_date
        )
        self._log_error(error)
        
        if try_previous_day and comic_date == date.today():
            # Try yesterday as fallback for today's comic
            yesterday = comic_date - timedelta(days=1)
            self.logger.info(f"Trying previous day ({yesterday}) as fallback for {comic_name}")
            
            # This would be called by the service layer to retry
            # We don't retry here to avoid circular dependencies
            return None
        
        raise error
    
    def get_user_friendly_message(self, error: ComicError) -> str:
        """
        Generate a user-friendly error message.
        
        Args:
            error: The error to generate a message for
            
        Returns:
            User-friendly error message
        """
        if error.error_type == ErrorType.NETWORK_ERROR:
            if isinstance(error, NetworkError) and error.status_code == 404:
                return "This comic is not available for the selected date. Try a different date."
            else:
                return "Unable to connect to the comic website. Please check your internet connection and try again."
        
        elif error.error_type == ErrorType.PARSING_ERROR:
            return "Unable to load the comic. The website format may have changed. Please try again later."
        
        elif error.error_type == ErrorType.CACHE_ERROR:
            return "There was an issue with local storage, but the comic should still load from the internet."
        
        elif error.error_type == ErrorType.COMIC_UNAVAILABLE:
            if isinstance(error, ComicUnavailableError):
                return f"The comic '{error.comic_name}' is not available for {error.comic_date.strftime('%B %d, %Y')}. Try a different date."
            else:
                return "This comic is not available for the selected date."
        
        else:
            return "An unexpected error occurred. Please try again."
    
    def get_recovery_suggestions(self, error: ComicError) -> List[str]:
        """
        Get recovery suggestions for an error.
        
        Args:
            error: The error to get suggestions for
            
        Returns:
            List of recovery suggestions
        """
        suggestions = []
        
        if error.error_type == ErrorType.NETWORK_ERROR:
            suggestions.extend([
                "Check your internet connection",
                "Try again in a few moments",
                "Try a different comic or date"
            ])
        
        elif error.error_type == ErrorType.PARSING_ERROR:
            suggestions.extend([
                "Try again later",
                "Try a different date",
                "Report this issue if it persists"
            ])
        
        elif error.error_type == ErrorType.COMIC_UNAVAILABLE:
            suggestions.extend([
                "Try the previous day",
                "Try a different date",
                "Check if this comic has content for this time period"
            ])
        
        elif error.error_type == ErrorType.CACHE_ERROR:
            suggestions.extend([
                "Clear the application cache",
                "Check available disk space",
                "The comic should still load from the internet"
            ])
        
        return suggestions
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics for monitoring and debugging.
        
        Returns:
            Dictionary with error statistics
        """
        return {
            'error_counts': {error_type.value: count for error_type, count in self.error_counts.items()},
            'recent_errors_count': len(self.recent_errors),
            'recent_errors': [
                {
                    'type': error.error_type.value,
                    'severity': error.severity.value,
                    'message': str(error),
                    'timestamp': error.timestamp
                }
                for error in self.recent_errors[-10:]  # Last 10 errors
            ]
        }
    
    def clear_error_statistics(self) -> None:
        """Clear error statistics and recent errors."""
        self.error_counts = {error_type: 0 for error_type in ErrorType}
        self.recent_errors.clear()
        self.logger.info("Error statistics cleared")