"""
Web scraping functionality for retrieving comic data from GoComics.com.
"""

import datetime
import logging
import os
import re
import threading
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests
from requests.exceptions import HTTPError, RequestException

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    cffi_requests = None
    HAS_CURL_CFFI = False

from models.data_models import ComicData, get_comic_definition
from services.bunny_shield_resolver import BunnyShieldResolver
from services.error_handler import ErrorHandler, NetworkError, ParsingError, ComicUnavailableError


class WebScrapingError(Exception):
    """Exception raised when web scraping fails."""
    pass


class BunnyShieldChallengeError(WebScrapingError):
    """Raised when GoComics returns a Bunny Shield challenge (VPN / IP block)."""
    pass


class RateLimitError(WebScrapingError):
    """Raised when GoComics returns a 429 Too Many Requests response."""
    pass


class AccessForbiddenError(WebScrapingError):
    """Raised when GoComics returns a 403 Forbidden response."""
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
    Uses curl_cffi (with fallback to requests) and BunnyShieldResolver for page
    retrieval, and BeautifulSoup for HTML parsing.
    """

    def __init__(
        self,
        timeout: int = 5,
        error_handler: Optional[ErrorHandler] = None,
        cache_dir: Optional[str] = None,
        debug: bool = False,
    ):
        """
        Initialize the WebScraper.

        Args:
            timeout: Timeout in seconds for HTTP requests
            error_handler: ErrorHandler instance for error management
            cache_dir: Optional directory path for storing Bunny Shield cookie state
            debug: Enable verbose debug logging for Bunny Shield resolution
        """
        self.timeout = timeout
        self.error_handler = error_handler or ErrorHandler()
        self.logger = logging.getLogger(__name__)
        self.shield_resolver = BunnyShieldResolver(cache_dir=cache_dir, debug=debug)
        self._session_lock = threading.Lock()

        self.impersonate: str = "chrome"
        self.user_agent: str = DEFAULT_BROWSER_HEADERS["User-Agent"]
        self.session = None

        cached = self.shield_resolver.load_cached_state()
        if cached:
            self._init_http_session(
                impersonate=cached.get("impersonate", "chrome"),
                cookies=cached.get("cookies"),
                user_agent=cached.get("user_agent"),
            )
        else:
            self._init_http_session(impersonate="chrome")

    def _init_http_session(
        self,
        impersonate: str = "chrome",
        cookies: Optional[Dict[str, str]] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Initializes or refreshes the persistent HTTP session with matching TLS fingerprint."""
        with self._session_lock:
            # Safely close any existing session to prevent dangling socket connections
            if self.session is not None:
                try:
                    self.session.close()
                except Exception:
                    pass
                self.session = None

            self.impersonate = impersonate if impersonate in ("chrome", "firefox") else "chrome"
            if user_agent:
                self.user_agent = user_agent
            elif self.impersonate == "firefox":
                self.user_agent = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"
                    if os.name == "nt"
                    else "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"
                )
            else:
                self.user_agent = DEFAULT_BROWSER_HEADERS["User-Agent"]

            if HAS_CURL_CFFI:
                try:
                    self.session = cffi_requests.Session(impersonate=self.impersonate)
                except Exception:
                    self.session = requests.Session()
            else:
                self.session = requests.Session()

            if cookies:
                for k, v in cookies.items():
                    self.session.cookies.set(k, v, domain=".gocomics.com")

    def _build_browser_headers(self) -> Dict[str, str]:
        """Builds request headers aligned with the active browser TLS impersonation."""
        headers = DEFAULT_BROWSER_HEADERS.copy()
        headers["User-Agent"] = self.user_agent

        ua_lower = self.user_agent.lower()
        if self.impersonate == "firefox" or "firefox" in ua_lower:
            # Firefox never sends Chromium Client Hints; sending them causes anti-bot blocks
            headers.pop("sec-ch-ua", None)
            headers.pop("sec-ch-ua-mobile", None)
            headers.pop("sec-ch-ua-platform", None)
        else:
            if "linux" in ua_lower:
                headers["sec-ch-ua-platform"] = '"Linux"'
            elif "macintosh" in ua_lower or "mac os" in ua_lower:
                headers["sec-ch-ua-platform"] = '"macOS"'
            else:
                headers["sec-ch-ua-platform"] = '"Windows"'

            ver_match = re.search(r"Chrome/(\d+)", self.user_agent)
            if ver_match:
                major = ver_match.group(1)
                headers["sec-ch-ua"] = (
                    f'"Google Chrome";v="{major}", "Chromium";v="{major}", "Not?A_Brand";v="24"'
                )

        return headers

    def _perform_get(self, url: str, headers: Dict[str, str], allow_redirects: bool):
        """
        Executes GET via self.session while normalizing curl_cffi exceptions into
        standard requests.exceptions.RequestException for ErrorHandler compatibility.
        """
        try:
            with self._session_lock:
                session = self.session
            return session.get(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=allow_redirects,
            )
        except RequestException:
            raise
        except Exception as exc:
            raise RequestException(str(exc)) from exc

    @staticmethod
    def _raise_for_status_compat(response, url: str) -> None:
        """Raises a standard requests.exceptions.HTTPError if status_code >= 400."""
        if response.status_code >= 400:
            mock_resp = type("MockResponse", (), {"status_code": response.status_code, "url": url})()
            raise HTTPError(
                f"{response.status_code} HTTP Error for url: {url}",
                response=mock_resp,
            )

    def fetch_page(
        self,
        url: str,
        allow_redirects: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        """
        Retrieve web page content and final URL using curl_cffi/requests with retry
        logic and automatic headless OS browser resolution for Bunny Shield challenges.
        """
        is_gocomics = "gocomics.com" in url.lower()
        fake_test_active = (
            os.environ.get("COMIC_BROWSER_FAKE_429") == "1"
            or os.environ.get("COMIC_BROWSER_FAKE_403") == "1"
        )

        def _fetch_with_requests() -> Tuple[str, str]:
            headers = self._build_browser_headers()
            response = self._perform_get(url, headers=headers, allow_redirects=allow_redirects)

            # If redirects are disabled and we got a redirect, treat as 404/Unavailable
            if not allow_redirects and 300 <= response.status_code < 400:
                raise WebScrapingError(
                    f"Comic not available for this date (redirected to {response.headers.get('Location')})"
                )

            html_text = response.text or ""
            final_url = str(response.url) if getattr(response, "url", None) else url

            if is_gocomics and not fake_test_active:
                # 1. Hard 429 rate-limit check: clear flagged cookie and never spawn browser
                if self._is_gocomics_429_page(html_text, "") or self.shield_resolver.is_rate_limited(
                    response.status_code, html_text, url
                ):
                    self.shield_resolver.clear_cached_state()
                    self._init_http_session(impersonate=self.impersonate)
                    if progress_callback:
                        progress_callback("GoComics rate limit (429) encountered.")
                    return html_text, final_url

                # 2. Hard 403 IP block check (BEFORE challenge solver!): never spawn browser
                resp_headers = getattr(response, "headers", None)
                if self._is_gocomics_403_page(html_text, "", headers=resp_headers) or self.shield_resolver.is_blocked(
                    response.status_code, html_text, url, headers=resp_headers
                ):
                    if progress_callback:
                        progress_callback("GoComics access forbidden (403).")
                    return html_text, final_url

                # 3. Solvable Bunny Shield JS PoW challenge check
                if self._is_gocomics_bunny_shield_page(
                    html_text, "", headers=resp_headers
                ) or self.shield_resolver.is_bunny_shield_challenge(
                    response.status_code, html_text, url, headers=resp_headers
                ):
                    self.logger.info(
                        f"Bunny Shield challenge detected on {url}. Invoking OS browser resolver..."
                    )
                    self.shield_resolver.clear_cached_state()
                    res = self.shield_resolver.solve_challenge(
                        url, progress_callback=progress_callback
                    )

                    if res.get("rate_limited"):
                        return res.get("html") or html_text, final_url

                    if res.get("ok"):
                        self._init_http_session(
                            impersonate=res.get("impersonate", "chrome"),
                            cookies=res.get("cookies"),
                            user_agent=res.get("user_agent"),
                        )
                        # If redirects are allowed and the browser already captured the comic HTML, reuse it directly
                        resolved_html = res.get("html") or ""
                        if allow_redirects and "og:image" in resolved_html.lower():
                            return resolved_html, url

                        # Otherwise, re-fetch with the newly minted cookies (preserving allow_redirects=False)
                        retry_headers = self._build_browser_headers()
                        retry_resp = self._perform_get(
                            url, headers=retry_headers, allow_redirects=allow_redirects
                        )
                        if not allow_redirects and 300 <= retry_resp.status_code < 400:
                            raise WebScrapingError(
                                f"Comic not available for this date (redirected to {retry_resp.headers.get('Location')})"
                            )
                        retry_url = str(retry_resp.url) if getattr(retry_resp, "url", None) else url
                        if retry_resp.status_code in (403, 429, 503) and retry_resp.text:
                            return retry_resp.text, retry_url
                        self._raise_for_status_compat(retry_resp, url)
                        if not retry_resp.text:
                            raise WebScrapingError(f"Empty response from {url}")
                        return retry_resp.text, retry_url

                    # If solver could not solve the challenge, raise BunnyShieldChallengeError directly
                    raise BunnyShieldChallengeError(
                        f"GoComics Bunny Shield security challenge could not be resolved for {url}"
                    )

                # 4. Hard 403 block check (when confirmed not a solvable challenge)
                if self._is_gocomics_403_page(html_text, "", headers=resp_headers):
                    return html_text, final_url

            # If GoComics returns 403 or 429 and provides HTML content, let the parser inspect it
            if is_gocomics and response.status_code in (403, 429, 503) and html_text:
                return html_text, final_url

            self._raise_for_status_compat(response, url)
            if not html_text:
                raise WebScrapingError(f"Empty response from {url}")
            return html_text, final_url

        try:
            return self.error_handler.retry_with_backoff(_fetch_with_requests)
        except (BunnyShieldChallengeError, RateLimitError, AccessForbiddenError):
            raise
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                mock_response = type("MockResponse", (), {"status_code": 404})()
                http_error = HTTPError(response=mock_response)
                date_match = re.search(r"/([\w-]+)/(\d{4})[-/](\d{2})[-/](\d{2})", url)
                if date_match:
                    comic_name = date_match.group(1)
                    try:
                        date_obj = datetime.date(
                            int(date_match.group(2)), int(date_match.group(3)), int(date_match.group(4))
                        )
                    except ValueError:
                        date_obj = datetime.date.today()
                    self.error_handler.handle_network_error(http_error, url, comic_name, date_obj)
                else:
                    url_parts = url.split("/")
                    if len(url_parts) >= 6:
                        comic_name = url_parts[-4] if len(url_parts) > 4 else "unknown"
                        try:
                            date_obj = datetime.date(
                                int(url_parts[-3]), int(url_parts[-2]), int(url_parts[-1])
                            )
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

    def parse_comic_data(
        self,
        html_content: str,
        comic_name: str,
        date: datetime.date,
        is_gocomics: bool = False,
    ) -> ComicData:
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
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract title safely first to allow checking block conditions even if title tag is unusual
            title = ""
            try:
                title = self._extract_title(soup)
            except Exception:
                pass

            # Detect GoComics security challenge or 429 Too Many Requests or 403 Forbidden (GoComics only)
            if is_gocomics:
                # 1. Check for 429 rate limit
                if os.environ.get("COMIC_BROWSER_FAKE_429") == "1" or self._is_gocomics_429_page(
                    html_content, title
                ):
                    raise RateLimitError(
                        f"GoComics 429 Too Many Requests detected for {comic_name} on {date}"
                    )

                # 2. Check for Bunny Shield challenge (CRITICAL: evaluate BEFORE 403 Forbidden!)
                if self._is_gocomics_bunny_shield_page(html_content, title):
                    raise BunnyShieldChallengeError(
                        f"GoComics Bunny Shield security challenge detected for {comic_name} on {date}"
                    )

                # 3. Check for hard 403 Forbidden
                if os.environ.get("COMIC_BROWSER_FAKE_403") == "1" or self._is_gocomics_403_page(
                    html_content, title
                ):
                    raise AccessForbiddenError(
                        f"GoComics 403 Forbidden detected for {comic_name} on {date}"
                    )

            if not title:
                title = self._extract_title(soup)

            image_url = self._extract_og_image(soup)

            # CRITICAL CHECK: Verify the returned page matches the requested date.
            # Comics Kingdom may return cached content for a different date at the
            # requested URL. If the title contains a different date, it's wrong.

            # 1. Check og:url, canonical link, and meta refresh for redirected/wrong date URL
            meta_urls = []
            og_url = soup.find("meta", property="og:url")
            if og_url and og_url.get("content"):
                meta_urls.append(og_url["content"])
            canonical = soup.find("link", rel="canonical")
            if canonical and canonical.get("href"):
                meta_urls.append(canonical["href"])
            refresh = soup.find("meta", id="__next-page-redirect")
            if refresh and refresh.get("content"):
                meta_urls.append(refresh["content"])

            for m_url in meta_urls:
                url_dates = re.findall(r"(\d{4}[-/]\d{2}[-/]\d{2})", m_url)
                if url_dates:
                    returned_url_date = url_dates[0].replace("/", "-")
                    requested_date_str = date.strftime("%Y-%m-%d")
                    if returned_url_date != requested_date_str:
                        raise ComicUnavailableError(
                            f"Comic {comic_name} not available for {date} (server returned comic for {returned_url_date})",
                            comic_name=comic_name,
                            comic_date=date,
                        )

            if title:
                # 2. Try to find a date in YYYY-MM-DD or YYYY/MM/DD format in the title
                title_dates = re.findall(r"(\d{4}[-/]\d{2}[-/]\d{2})", title)
                if title_dates:
                    returned_date_str = title_dates[0].replace("/", "-")
                    requested_date_str = date.strftime("%Y-%m-%d")
                    if returned_date_str != requested_date_str:
                        raise ComicUnavailableError(
                            f"Comic {comic_name} not available for {date} (server returned title for {returned_date_str})",
                            comic_name=comic_name,
                            comic_date=date,
                        )
                else:
                    # 3. Try to find Month DD, YYYY format (GoComics style, e.g. June 28, 2026)
                    month_match = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", title)
                    if month_match:
                        month_str, day_str, year_str = month_match.groups()
                        try:
                            parsed_date = None
                            try:
                                parsed_date = datetime.datetime.strptime(
                                    f"{month_str} {day_str}, {year_str}", "%B %d, %Y"
                                ).date()
                            except ValueError:
                                try:
                                    parsed_date = datetime.datetime.strptime(
                                        f"{month_str} {day_str}, {year_str}", "%b %d, %Y"
                                    ).date()
                                except ValueError:
                                    pass

                            if parsed_date and parsed_date != date:
                                raise ComicUnavailableError(
                                    f"Comic {comic_name} not available for {date} (server returned title date {parsed_date.strftime('%Y-%m-%d')})",
                                    comic_name=comic_name,
                                    comic_date=date,
                                )
                        except ComicUnavailableError:
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
                author=author,
            )

        except (WebScrapingError, ComicUnavailableError):
            # Don't swallow date mismatch or unavailability errors - let them propagate
            raise
        except Exception as e:
            try:
                fallback_result = self.error_handler.handle_parsing_error(
                    e, html_content, comic_name, date
                )
                if fallback_result:
                    self.logger.info(f"Fallback parsing successful for {comic_name} on {date}")
                    return fallback_result
            except ParsingError:
                pass

            self.logger.error(f"Failed to parse comic data: {e}")
            raise WebScrapingError(f"Failed to parse comic data: {e}")

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML title tag or og:title."""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        title_tags = soup.find_all("title")
        for tag in title_tags:
            text = tag.get_text().strip()
            if text and text.lower() != "gocomics":
                return text

        if title_tags and title_tags[0].get_text().strip():
            return title_tags[0].get_text().strip()

        raise WebScrapingError("No title tag found")

    def _extract_og_image(self, soup: BeautifulSoup) -> str:
        """Extract image URL from og:image meta property."""
        og_image = soup.find("meta", property="og:image")
        if not og_image or not og_image.get("content"):
            raise WebScrapingError("No og:image meta property found")

        image_url = og_image["content"].strip()
        if not image_url:
            raise WebScrapingError("Empty og:image content")

        return image_url

    def _extract_og_image_width(self, soup: BeautifulSoup) -> int:
        """Extract image width from og:image:width meta property."""
        og_width = soup.find("meta", property="og:image:width")
        if not og_width or not og_width.get("content"):
            return 900

        try:
            width = int(og_width["content"])
            return width if width > 0 else 900
        except (ValueError, TypeError):
            return 900

    def _extract_og_image_height(self, soup: BeautifulSoup) -> int:
        """Extract image height from og:image:height meta property."""
        og_height = soup.find("meta", property="og:image:height")
        if not og_height or not og_height.get("content"):
            return 300

        try:
            height = int(og_height["content"])
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
        author_match = re.search(r"by\s+([^|]+?)(?:\s+for|\s*\|)", title, re.IGNORECASE)
        if author_match:
            return author_match.group(1).strip()

        comic_def = get_comic_definition(comic_name)
        if comic_def and comic_def.author:
            return comic_def.author

        return "Unknown Author"

    def _is_gocomics_bunny_shield_page(
        self, html_content: str, title: str, headers: Optional[Any] = None
    ) -> bool:
        """
        Check if a page represents a GoComics Bunny Shield challenge.
        A page with an og:image meta tag is a rendered comic page, not a challenge.
        Pages representing 403 blocks or 429 rate limits are NOT challenges.
        """
        if not html_content and not headers:
            return False
        lower_html = (html_content or "").lower()
        if "og:image" in lower_html:
            return False
        if self._is_gocomics_403_page(html_content, title, headers=headers):
            return False
        if self._is_gocomics_429_page(html_content, title):
            return False

        if headers:
            try:
                headers_lower = {str(k).lower(): str(v).lower() for k, v in headers.items()}
                if headers_lower.get("cdn-challenge") == "true":
                    return True
            except Exception:
                pass

        if title and "establishing a secure connection" in title.lower():
            return True
        if "establishing a secure connection" in lower_html:
            return True
        if "shield-templates-prod.b-cdn.net" in lower_html and "challenge.html" in lower_html:
            return True
        if (
            "data-pow" in lower_html
            or "shield-challenge.js" in lower_html
            or "challenge-styles.css" in lower_html
            or "<title>bunny shield" in lower_html
        ):
            return True
        return False

    def _is_gocomics_429_page(self, html_content: str, title: str) -> bool:
        """
        Check if a page represents a GoComics 429 Too Many Requests response.
        Detected if:
        1) The title includes '429 Too Many Requests'
        2) The body includes both 'shield-templates-prod.b-cdn.net' and 'ratelimit.html'
        """
        if not html_content:
            return False
        lower_html = html_content.lower()
        if "og:image" in lower_html:
            return False
        if title and "429 too many requests" in title.lower():
            return True
        if "shield-templates-prod.b-cdn.net" in lower_html and "ratelimit.html" in lower_html:
            return True
        return False

    def _is_gocomics_403_page(
        self, html_content: str, title: str, headers: Optional[Any] = None
    ) -> bool:
        """
        Check if a page represents a GoComics 403 Forbidden response.
        Detected if:
        1) The body includes 'block.html'
        2) The html includes '<title>403 Forbidden</title>' (and is not a challenge)
        3) The body includes 'blocked from accessing this page' or 'triggered the service and blocked your request'
        """
        if not html_content and not headers and not title:
            return False
        lower_html = (html_content or "").lower()
        if "og:image" in lower_html:
            return False

        # Explicit solvable challenge indicators -> NEVER a hard 403 block!
        if headers:
            try:
                headers_lower = {str(k).lower(): str(v).lower() for k, v in headers.items()}
                if headers_lower.get("cdn-challenge") == "true":
                    return False
            except Exception:
                pass

        if "establishing a secure connection" in lower_html or "shield-challenge.js" in lower_html:
            return False

        # Hard 403 block indicators
        if "shield-templates-prod.b-cdn.net" in lower_html and "block.html" in lower_html:
            return True
        if "<title>403 forbidden</title>" in lower_html:
            return True
        if title and "403 forbidden" in title.lower():
            return True
        if (
            "blocked from accessing this page" in lower_html
            or "triggered the service and blocked your request" in lower_html
        ):
            return True
        return False

    def get_comic_data(
        self,
        comic_name: str,
        base_url: str,
        date: datetime.date,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> ComicData:
        """
        Retrieve and parse comic data for a specific date.
        """
        comic_def = get_comic_definition(comic_name)
        is_gocomics = "gocomics.com" in base_url.lower()

        # If --fake429 CLI flag is active and this is GoComics, simulate 429 page immediately
        if is_gocomics and os.environ.get("COMIC_BROWSER_FAKE_429") == "1":
            raise RateLimitError(
                f"GoComics 429 Too Many Requests detected for {comic_name} on {date}"
            )
        if (
            comic_def
            and getattr(comic_def, "is_custom", False)
            and getattr(comic_def, "custom_url_pattern", "")
        ):
            url_pattern = comic_def.custom_url_pattern
            url_pattern = url_pattern.replace("%YYYY%", f"{date.year:04d}")
            url_pattern = url_pattern.replace("%YY%", f"{date.year % 100:02d}")
            url_pattern = url_pattern.replace("%MM%", f"{date.month:02d}")
            url_pattern = url_pattern.replace("%DD%", f"{date.day:02d}")

            image_url = base_url.rstrip("/") + "/" + url_pattern.lstrip("/")

            try:
                headers = DEFAULT_IMAGE_HEADERS.copy()
                response = requests.head(image_url, headers=headers, timeout=self.timeout)
                if response.status_code == 405:  # Method Not Allowed
                    response = requests.get(
                        image_url, headers=headers, stream=True, timeout=self.timeout
                    )
                    response.close()
                response.raise_for_status()
            except HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    raise WebScrapingError("Comic not available for this date (404 Not Found)")
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
                author=comic_def.author,
            )

        # Handle different URL formats per provider
        if is_gocomics:
            url = f"{base_url}/{date.year:04d}/{date.month:02d}/{date.day:02d}"
        elif "comicskingdom.com" in base_url.lower():
            url = f"{base_url}/{date.year:04d}-{date.month:02d}-{date.day:02d}"
        else:
            url = f"{base_url}/{date.year:04d}/{date.month:02d}/{date.day:02d}"

        # Disable redirects for past dates to catch gaps early (GoComics redirects missing past dates to Today)
        # We define "past" as older than yesterday to allow for TZ differences
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        allow_redirects = (date >= yesterday) if is_gocomics else True

        html_content, final_url = self.fetch_page(
            url, allow_redirects=allow_redirects, progress_callback=progress_callback
        )

        # Check if final_url contains a date pattern different from expected (GoComics redirects)
        if is_gocomics:
            url_dates = re.findall(r"(\d{4}[-/]\d{2}[-/]\d{2})", final_url)
            if url_dates:
                returned_url_date = url_dates[0].replace("/", "-")
                requested_date_str = date.strftime("%Y-%m-%d")
                if returned_url_date != requested_date_str:
                    raise ComicUnavailableError(
                        f"Comic {comic_name} not available for {date} (server redirected to {returned_url_date})",
                        comic_name=comic_name,
                        comic_date=date,
                    )

        comic_data = self.parse_comic_data(
            html_content, comic_name, date, is_gocomics=is_gocomics
        )

        return comic_data
