"""
Web scraping functionality for retrieving comic data from GoComics.com.
"""

import re
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from models.data_models import ComicData, get_comic_definition
import datetime
import requests
from requests.exceptions import HTTPError, RequestException

from services.error_handler import ErrorHandler, NetworkError, ParsingError


class WebScrapingError(Exception):
    """Exception raised when web scraping fails."""
    pass


class BunnyShieldChallengeError(WebScrapingError):
    """Raised when GoComics returns a Bunny Shield challenge (VPN / IP block)."""
    pass


class RateLimitError(WebScrapingError):
    """Raised when GoComics returns a 429 Too Many Requests response."""
    pass


# Common modern browser headers with Chromium Client Hints
DEFAULT_BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'sec-ch-ua': '"Google Chrome";v="135", "Chromium";v="135", "Not?A_Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

DEFAULT_IMAGE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site',
    'sec-ch-ua': '"Google Chrome";v="135", "Chromium";v="135", "Not?A_Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


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
        self.logger = logging.getLogger(__name__)
        
    def fetch_page(self, url: str, allow_redirects: bool = True) -> Tuple[str, str]:
        """
        Retrieve web page content and final URL using requests with retry logic.
        """
        def _fetch_with_requests():
            headers = DEFAULT_BROWSER_HEADERS.copy()
            response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=allow_redirects)
            
            # If redirects are disabled and we got a redirect, treat as 404/Unavailable
            if not allow_redirects and 300 <= response.status_code < 400:
                raise WebScrapingError(f"Comic not available for this date (redirected to {response.headers.get('Location')})")
                
            # If GoComics returns 403 or 429 and provides HTML content, let the parser inspect it
            if 'gocomics.com' in url and response.status_code in (403, 429) and response.text:
                return response.text, response.url

            response.raise_for_status()
            if not response.text:
                raise WebScrapingError(f"Empty response from {url}")
            return response.text, response.url
        
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
            self.logger.error(f"Request failed for {url}: {e}")
            raise WebScrapingError(f"Failed to fetch {url}: {e}")
        except RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            raise WebScrapingError(f"Failed to fetch {url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {url}: {e}")
            raise WebScrapingError(f"Unexpected error fetching {url}: {e}")


    def parse_comic_data(self, html_content: str, comic_name: str, date: datetime.date, is_gocomics: bool = False) -> ComicData:
        """
        Parse HTML content to extract comic data with fallback mechanisms.
        
        Args:
            html_content: Raw HTML content
            comic_name: Name of the comic strip
            date: Date of the comic
            is_gocomics: Whether the comic source is GoComics
            
        Returns:
            ComicData object with extracted information
            
        Raises:
            WebScrapingError: If required data cannot be extracted
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract title safely first to allow checking block conditions even if title tag is unusual
            title = ""
            try:
                title = self._extract_title(soup)
            except Exception:
                pass

            # Detect GoComics security challenge or 429 Too Many Requests (GoComics only)
            if is_gocomics:
                import os
                if os.environ.get("COMIC_BROWSER_FAKE_429") == "1" or self._is_gocomics_429_page(html_content, title):
                    raise RateLimitError(
                        f"GoComics 429 Too Many Requests detected for {comic_name} on {date}"
                    )
                if self._is_gocomics_bunny_shield_page(html_content, title):
                    raise BunnyShieldChallengeError(
                        f"GoComics Bunny Shield security challenge detected for {comic_name} on {date}"
                    )

            if not title:
                title = self._extract_title(soup)

            image_url = self._extract_og_image(soup)

            # CRITICAL CHECK: Verify the returned page matches the requested date.
            # Comics Kingdom may return cached content for a different date at the
            # requested URL. If the title contains a different date, it's wrong.
            import re
            
            # 1. Check og:url, canonical link, and meta refresh for redirected/wrong date URL
            meta_urls = []
            og_url = soup.find('meta', property='og:url')
            if og_url and og_url.get('content'):
                meta_urls.append(og_url['content'])
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                meta_urls.append(canonical['href'])
            refresh = soup.find('meta', id='__next-page-redirect')
            if refresh and refresh.get('content'):
                meta_urls.append(refresh['content'])
                
            for m_url in meta_urls:
                url_dates = re.findall(r'(\d{4}[-/]\d{2}[-/]\d{2})', m_url)
                if url_dates:
                    returned_url_date = url_dates[0].replace('/', '-')
                    requested_date_str = date.strftime("%Y-%m-%d")
                    if returned_url_date != requested_date_str:
                        raise WebScrapingError(
                            f"Server returned comic for wrong date {returned_url_date} in og:url/canonical instead of requested {requested_date_str}"
                        )

            if title:
                # 2. Try to find a date in YYYY-MM-DD or YYYY/MM/DD format in the title
                title_dates = re.findall(r'(\d{4}[-/]\d{2}[-/]\d{2})', title)
                if title_dates:
                    returned_date_str = title_dates[0].replace('/', '-')
                    requested_date_str = date.strftime("%Y-%m-%d")
                    if returned_date_str != requested_date_str:
                        raise WebScrapingError(
                            f"Server returned comic for wrong date {returned_date_str} instead of requested {requested_date_str}"
                        )
                else:
                    # 3. Try to find Month DD, YYYY format (GoComics style, e.g. June 28, 2026)
                    month_match = re.search(r'([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})', title)
                    if month_match:
                        month_str, day_str, year_str = month_match.groups()
                        try:
                            parsed_date = None
                            try:
                                parsed_date = datetime.datetime.strptime(f"{month_str} {day_str}, {year_str}", "%B %d, %Y").date()
                            except ValueError:
                                try:
                                    parsed_date = datetime.datetime.strptime(f"{month_str} {day_str}, {year_str}", "%b %d, %Y").date()
                                except ValueError:
                                    pass
                            
                            if parsed_date and parsed_date != date:
                                raise WebScrapingError(
                                    f"Server returned comic for wrong date {parsed_date.strftime('%Y-%m-%d')} instead of requested {date.strftime('%Y-%m-%d')}"
                                )
                        except WebScrapingError:
                            raise
                        except Exception:
                            pass

            image_width = self._extract_og_image_width(soup)
            image_height = self._extract_og_image_height(soup)
            image_format = ""  # Will be detected by CacheManager during download
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
                    self.logger.info(f"Fallback parsing successful for {comic_name} on {date}")
                    return fallback_result
            except ParsingError:
                pass

            self.logger.error(f"Failed to parse comic data: {e}")
            raise WebScrapingError(f"Failed to parse comic data: {e}")
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML title tag or og:title."""
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
            
        title_tags = soup.find_all('title')
        for tag in title_tags:
            text = tag.get_text().strip()
            if text and text.lower() != 'gocomics':
                return text
                
        if title_tags and title_tags[0].get_text().strip():
            return title_tags[0].get_text().strip()
            
        raise WebScrapingError("No title tag found")
    
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
        
        comic_def = get_comic_definition(comic_name)
        if comic_def and comic_def.author:
            return comic_def.author
        
        return 'Unknown Author'
    
    def _is_gocomics_bunny_shield_page(self, html_content: str, title: str) -> bool:
        """
        Check if a page represents a GoComics Bunny Shield challenge.
        Detected if EITHER:
        1) The title includes 'Establishing a secure connection'
        2) The body includes a reference to 'shield-templates-prod.b-cdn.net' and 'challenge.html'
        """
        if title and "establishing a secure connection" in title.lower():
            return True
        if html_content:
            lower_html = html_content.lower()
            if "shield-templates-prod.b-cdn.net" in lower_html and "challenge.html" in lower_html:
                return True
        return False

    def _is_gocomics_429_page(self, html_content: str, title: str) -> bool:
        """
        Check if a page represents a GoComics 429 Too Many Requests response.
        Detected if EITHER:
        1) The title includes '429 Too Many Requests'
        2) The body includes a reference to 'shield-templates-prod.b-cdn.net' and 'ratelimit.html'
        """
        if title and "429 too many requests" in title.lower():
            return True
        if html_content:
            lower_html = html_content.lower()
            if "shield-templates-prod.b-cdn.net" in lower_html and "ratelimit.html" in lower_html:
                return True
        return False

    def get_comic_data(self, comic_name: str, base_url: str, date: datetime.date) -> ComicData:
        """
        Retrieve and parse comic data for a specific date.
        """
        comic_def = get_comic_definition(comic_name)
        is_gocomics = ('gocomics.com' in base_url.lower())

        # If --fake429 CLI flag is active and this is GoComics, simulate 429 page immediately
        import os
        if is_gocomics and os.environ.get("COMIC_BROWSER_FAKE_429") == "1":
            raise RateLimitError(
                f"GoComics 429 Too Many Requests detected for {comic_name} on {date}"
            )
        if comic_def and getattr(comic_def, 'is_custom', False) and getattr(comic_def, 'custom_url_pattern', ''):
            url_pattern = comic_def.custom_url_pattern
            url_pattern = url_pattern.replace("%YYYY%", f"{date.year:04d}")
            url_pattern = url_pattern.replace("%YY%", f"{date.year % 100:02d}")
            url_pattern = url_pattern.replace("%MM%", f"{date.month:02d}")
            url_pattern = url_pattern.replace("%DD%", f"{date.day:02d}")
            
            image_url = base_url.rstrip("/") + "/" + url_pattern.lstrip("/")
            
            try:
                headers = DEFAULT_IMAGE_HEADERS.copy()
                response = requests.head(image_url, headers=headers, timeout=self.timeout)
                if response.status_code == 405: # Method Not Allowed
                    response = requests.get(image_url, headers=headers, stream=True, timeout=self.timeout)
                    response.close()
                response.raise_for_status()
            except HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    raise WebScrapingError(f"Comic not available for this date (404 Not Found)")
                raise WebScrapingError(f"Failed to fetch {image_url}: {e}")
            except Exception as e:
                raise WebScrapingError(f"Failed to fetch {image_url}: {e}")
                
            return ComicData(
                comic_name=comic_name,
                date=date,
                title=f"{comic_def.display_name} for {date.strftime('%B %d, %Y')}",
                image_url=image_url,
                image_width=900,
                image_height=300,
                image_format="",
                author=comic_def.author
            )

        # Handle different URL formats per provider
        if is_gocomics:
            url = f"{base_url}/{date.year:04d}/{date.month:02d}/{date.day:02d}"
        elif 'comicskingdom.com' in base_url.lower():
            url = f"{base_url}/{date.year:04d}-{date.month:02d}-{date.day:02d}"
        else:
            url = f"{base_url}/{date.year:04d}/{date.month:02d}/{date.day:02d}"

        # Disable redirects for past dates to catch gaps early (GoComics redirects missing past dates to Today)
        # We define "past" as older than yesterday to allow for TZ differences
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        allow_redirects = (date >= yesterday) if is_gocomics else True

        html_content, final_url = self.fetch_page(url, allow_redirects=allow_redirects)

        # Check if final_url contains a date pattern different from expected (GoComics redirects)
        if is_gocomics:
            import re
            url_dates = re.findall(r'(\d{4}[-/]\d{2}[-/]\d{2})', final_url)
            if url_dates:
                returned_url_date = url_dates[0].replace('/', '-')
                requested_date_str = date.strftime("%Y-%m-%d")
                if returned_url_date != requested_date_str:
                    raise WebScrapingError(
                        f"Server redirected to comic for wrong date {returned_url_date} instead of requested {requested_date_str}"
                    )

        comic_data = self.parse_comic_data(html_content, comic_name, date, is_gocomics=is_gocomics)

        return comic_data

