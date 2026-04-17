"""
Web scraping functionality for retrieving comic data from GoComics.com.
"""

import re
# import logging
from typing import Optional
from bs4 import BeautifulSoup
from models.data_models import ComicData
import datetime
import requests
from requests.exceptions import HTTPError, RequestException

from services.error_handler import ErrorHandler, NetworkError, ParsingError


class WebScrapingError(Exception):
    """Exception raised when web scraping fails."""
    pass


class WebScraper:
    """
    Web scraper for retrieving and parsing comic data from GoComics.com.
    Uses requests for page retrieval and BeautifulSoup for HTML parsing.
    """
    
    def __init__(self, timeout: int = 5, error_handler: Optional[ErrorHandler] = None):
        """
        Initialize the WebScraper.
        
        Args:
            timeout: Timeout in seconds for HTTP requests
            error_handler: ErrorHandler instance for error management
        """
        self.timeout = timeout
        self.error_handler = error_handler or ErrorHandler()
        # self.logger = logging.getLogger(__name__)
        
    def fetch_page(self, url: str) -> str:
        """
        Retrieve web page content using requests with retry logic.

        Args:
            url: The URL to fetch

        Returns:
            HTML content as string

        Raises:
            WebScrapingError: If the page cannot be retrieved
        """
        def _fetch_with_requests():
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            if not response.text:
                raise WebScrapingError(f"Empty response from {url}")
            self._last_fetched_url = response.url  # track final URL after redirects
            return response.text        
        try:
            return self.error_handler.retry_with_backoff(_fetch_with_requests)
        except HTTPError as e:
            if e.response.status_code == 404:
                mock_response = type('MockResponse', (), {'status_code': 404})()
                http_error = HTTPError(response=mock_response)
                url_parts = url.split('/')
                if len(url_parts) >= 6:
                    comic_name = url_parts[-4] if len(url_parts) > 4 else 'unknown'
                    try:
                        date_obj = datetime.date(int(url_parts[-3]), int(url_parts[-2]), int(url_parts[-1]))
                    except (ValueError, IndexError):
                        date_obj = datetime.date.today()
                    self.error_handler.handle_network_error(http_error, url, comic_name, date_obj)
            # self.logger.error(f"Request failed for {url}: {e}")
            raise WebScrapingError(f"Failed to fetch {url}: {e}")
        except RequestException as e:
            # self.logger.error(f"Request failed for {url}: {e}")
            raise WebScrapingError(f"Failed to fetch {url}: {e}")
        except Exception as e:
            # self.logger.error(f"Unexpected error fetching {url}: {e}")
            raise WebScrapingError(f"Unexpected error fetching {url}: {e}")

    def parse_comic_data(self, html_content: str, comic_name: str, date: datetime.date) -> ComicData:
        """
        Parse HTML content to extract comic data with fallback mechanisms.
        
        Args:
            html_content: Raw HTML content
            comic_name: Name of the comic strip
            date: Date of the comic
            
        Returns:
            ComicData object with extracted information
            
        Raises:
            WebScrapingError: If required data cannot be extracted
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            title = self._extract_title(soup)

            # Detect Bunny Shield / security challenge (GoComics IP block)
            page_text = soup.get_text()
            if "security service" in page_text and ("secure connection" in page_text or "Please enable JavaScript" in page_text):
                raise WebScrapingError(
                    f"GoComics security challenge detected — IP may be blocked for {comic_name} on {date}"
                )

            image_url = self._extract_og_image(soup)

            # CRITICAL CHECK: Verify the returned page matches the requested date.
            # Comics Kingdom may return cached content for a different date at the
            # requested URL. If the title contains a different date, it's wrong.
            if title:
                # Try to find a date in YYYY-MM-DD format in the title
                import re
                title_dates = re.findall(r'(\d{4}-\d{2}-\d{2})', title)
                if title_dates:
                    returned_date_str = title_dates[0]
                    requested_date_str = date.strftime("%Y-%m-%d")
                    if returned_date_str != requested_date_str:
                        raise WebScrapingError(
                            f"Server returned comic for wrong date {returned_date_str} instead of requested {requested_date_str}"
                        )

            image_width = self._extract_og_image_width(soup)
            image_height = self._extract_og_image_height(soup)
            image_format = self._detect_image_format(image_url)
            author = self._extract_author(title, comic_name)
            
            return ComicData(
                comic_name=comic_name,
                date=date,
                title=title,
                image_url=image_url,
                image_width=image_width,
                image_height=image_height,
                image_format=image_format,
                author=author
            )

        except WebScrapingError:
            # Don't swallow date mismatch errors - let them propagate
            raise
        except Exception as e:
            try:
                fallback_result = self.error_handler.handle_parsing_error(e, html_content, comic_name, date)
                if fallback_result:
                    # self.logger.info(f"Fallback parsing successful for {comic_name} on {date}")
                    return fallback_result
            except ParsingError:
                pass

            # self.logger.error(f"Failed to parse comic data: {e}")
            raise WebScrapingError(f"Failed to parse comic data: {e}")
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML title tag."""
        title_tag = soup.find('title')
        if not title_tag:
            raise WebScrapingError("No title tag found")
        
        title = title_tag.get_text().strip()
        if not title:
            raise WebScrapingError("Empty title tag")
            
        return title
    
    def _extract_og_image(self, soup: BeautifulSoup) -> str:
        """Extract image URL from og:image meta property."""
        og_image = soup.find('meta', property='og:image')
        if not og_image or not og_image.get('content'):
            raise WebScrapingError("No og:image meta property found")
        
        image_url = og_image['content'].strip()
        if not image_url:
            raise WebScrapingError("Empty og:image content")
            
        return image_url
    
    def _extract_og_image_width(self, soup: BeautifulSoup) -> int:
        """Extract image width from og:image:width meta property."""
        og_width = soup.find('meta', property='og:image:width')
        if not og_width or not og_width.get('content'):
            return 900
        
        try:
            width = int(og_width['content'])
            return width if width > 0 else 900
        except (ValueError, TypeError):
            return 900
    
    def _extract_og_image_height(self, soup: BeautifulSoup) -> int:
        """Extract image height from og:image:height meta property."""
        og_height = soup.find('meta', property='og:image:height')
        if not og_height or not og_height.get('content'):
            return 300
        
        try:
            height = int(og_height['content'])
            return height if height > 0 else 300
        except (ValueError, TypeError):
            return 300
    
    def _detect_image_format(self, image_url: str) -> str:
        """
        Return a default image format — actual format is detected from the
        saved file in cache_manager after download, avoiding a redundant
        network request.
        """
        return 'jpeg'
    
    def _extract_author(self, title: str, comic_name: str) -> str:
        """
        Extract author from title or use default mapping.
        
        Args:
            title: Comic title string
            comic_name: Name of the comic strip
            
        Returns:
            Author name
        """
        author_match = re.search(r'by\s+([^|]+?)(?:\s+for|\s*\|)', title, re.IGNORECASE)
        if author_match:
            return author_match.group(1).strip()
        
        author_mapping = {
            'calvinandhobbes': 'Bill Watterson',
            'peanuts': 'Charles M. Schulz',
            'peanuts-begins': 'Charles M. Schulz',
            'garfield': 'Jim Davis',
            'wizardofid': 'Brant Parker and Johnny Hart',            
            'pearlsbeforeswine': 'Stephan Pastis',
            'shoe': 'Jeff MacNelly',
            'bc': 'Johnny Hart',
            'back-to-bc': 'Johnny Hart',
            'pickles': 'Brian Crane',
            'wumo': 'Mikael Wulff and Anders Morgenthaler',
            'speedbump': 'Dave Coverly',
            'freerange': 'Bill Whitehead',
            'offthemark': 'Mark Parisi',
            'mother-goose-and-grimm': 'Mike Peters',
            'theflyingmccoys': 'Gary McCoy and Glenn McCoy',
            'duplex': 'Glenn McCoy',
            'realitycheck': 'Dave Whamond',
            'adamathome': 'Rob Harrell',
            'ziggy': 'Tom Wilson & Tom II'
        }
        
        return author_mapping.get(comic_name, 'Unknown Author')
    
    def get_comic_data(self, comic_name: str, base_url: str, date: datetime.date) -> ComicData:
        """
        Retrieve and parse comic data for a specific date.

        Args:
            comic_name: Name of the comic strip
            base_url: Base URL for the comic
            date: Date to retrieve

        Returns:
            ComicData object with all extracted information

        Raises:
            WebScrapingError: If comic data cannot be retrieved or parsed
        """
        # Handle different URL formats for GoComics vs Comics Kingdom
        if 'comicskingdom.com' in base_url:
            url = f"{base_url}/{date.year:04d}-{date.month:02d}-{date.day:02d}"
        else:
            url = f"{base_url}/{date.year:04d}/{date.month:02d}/{date.day:02d}"

        html_content = self.fetch_page(url)
        actual_url = self._last_fetched_url  # Track where we actually landed

        # GoComics uses a meta refresh redirect for dates with no comic
        # (e.g. Foxtrot on a non-Sunday redirects to the previous Sunday).
        # requests doesn't follow meta refresh, so we detect and handle it here.
        soup_check = BeautifulSoup(html_content, 'html.parser')
        meta_refresh = soup_check.find('meta', attrs={'http-equiv': lambda x: x and x.lower() == 'refresh'})
        if meta_refresh and meta_refresh.get('content'):
            import re
            m = re.search(r'url=(.+)', meta_refresh['content'], re.IGNORECASE)
            if m:
                redirect_path = m.group(1).strip()
                # Extract the date from the redirect URL
                date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})', redirect_path)
                if date_match:
                    actual_date = datetime.date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
                    if actual_date != date:
                        raise WebScrapingError(
                            f"GoComics meta-refresh to {actual_date} instead of requested {date} for {comic_name}"
                        )

        comic_data = self.parse_comic_data(html_content, comic_name, date)
        return comic_data
