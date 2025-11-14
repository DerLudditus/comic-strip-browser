"""
Core data models for the comic strip browser application.

This module contains the dataclasses that represent comic data, comic definitions,
and cache entries used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class ComicData:
    """
    Represents a single comic strip with all its metadata.
    
    This dataclass stores all the information needed to display a comic strip,
    including the image URL, dimensions, title, and caching information.
    """
    comic_name: str
    date: date
    title: str
    image_url: str
    image_width: int
    image_height: int
    image_format: str
    author: str
    cached_image_path: Optional[str] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate the comic data after initialization."""
        if not self.comic_name or not isinstance(self.comic_name, str):
            raise ValueError("comic_name must be a non-empty string")
        
        if not isinstance(self.date, date):
            raise ValueError("date must be a datetime.date object")
        
        if not self.title or not isinstance(self.title, str):
            raise ValueError("title must be a non-empty string")
        
        if not self.image_url or not isinstance(self.image_url, str):
            raise ValueError("image_url must be a non-empty string")
        
        if not isinstance(self.image_width, int) or self.image_width <= 0:
            raise ValueError("image_width must be a positive integer")
        
        if not isinstance(self.image_height, int) or self.image_height <= 0:
            raise ValueError("image_height must be a positive integer")
        
        if not self.image_format or not isinstance(self.image_format, str):
            raise ValueError("image_format must be a non-empty string")
        
        if not self.author or not isinstance(self.author, str):
            raise ValueError("author must be a non-empty string")


@dataclass
class ComicDefinition:
    """
    Represents the definition of a comic strip with its metadata and configuration.
    
    This dataclass contains the static information about each comic strip,
    including its name, display name, base URL, and author information.
    """
    name: str
    display_name: str
    base_url: str
    author: str
    earliest_date: Optional[date] = None
    
    def __post_init__(self):
        """Validate the comic definition after initialization."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string")
        
        if not self.display_name or not isinstance(self.display_name, str):
            raise ValueError("display_name must be a non-empty string")
        
        if not self.base_url or not isinstance(self.base_url, str):
            raise ValueError("base_url must be a non-empty string")
        
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("base_url must be a valid HTTP/HTTPS URL")
        
        if not self.author or not isinstance(self.author, str):
            raise ValueError("author must be a non-empty string")
        
        if self.earliest_date is not None and not isinstance(self.earliest_date, date):
            raise ValueError("earliest_date must be a datetime.date object or None")


@dataclass
class CacheEntry:
    """
    Represents a cached comic entry with access tracking information.
    
    This dataclass is used by the cache management system to track
    comic data along with access patterns for LRU cache implementation.
    """
    comic_data: ComicData
    access_count: int
    last_accessed: datetime
    file_size: int
    
    def __post_init__(self):
        """Validate the cache entry after initialization."""
        if not isinstance(self.comic_data, ComicData):
            raise ValueError("comic_data must be a ComicData instance")
        
        if not isinstance(self.access_count, int) or self.access_count < 0:
            raise ValueError("access_count must be a non-negative integer")
        
        if not isinstance(self.last_accessed, datetime):
            raise ValueError("last_accessed must be a datetime object")
        
        if not isinstance(self.file_size, int) or self.file_size < 0:
            raise ValueError("file_size must be a non-negative integer")


# Predefined comic definitions for the 15 supported comic strips
# Earliest dates are hard-coded based on GoComics.com availability
COMIC_DEFINITIONS = [
    ComicDefinition(
        name="calvinandhobbes",
        display_name="Calvin and Hobbes",
        base_url="https://www.gocomics.com/calvinandhobbes",
        author="Bill Watterson",
        earliest_date=date(1985, 11, 18)  # GoComics availability, not original publication
    ),
    ComicDefinition(
        name="peanuts",
        display_name="Peanuts",
        base_url="https://www.gocomics.com/peanuts",
        author="Charles M. Schulz",
        earliest_date=date(1950, 10, 16)
    ),
    ComicDefinition(
        name="peanuts-begins",
        display_name="Peanuts Begins",
        base_url="https://www.gocomics.com/peanuts-begins",
        author="Charles M. Schulz",
        earliest_date=date(1950, 10, 16)  # Recent reprint series; for old dates can be identical to Peanuts, only in color
    ),
    ComicDefinition(
        name="garfield",
        display_name="Garfield",
        base_url="https://www.gocomics.com/garfield",
        author="Jim Davis",
        earliest_date=date(1978, 6, 19)
    ),
    ComicDefinition(
        name="wizardofid",
        display_name="Wizard of Id",
        base_url="https://www.gocomics.com/wizardofid",
        author="Brant Parker and Johnny Hart",
        earliest_date=date(2002, 1, 1)  # Limited GoComics availability
    ),
    ComicDefinition(
        name="wizard-of-id-classics",
        display_name="Wizard of Id Classics",
        base_url="https://www.gocomics.com/wizard-of-id-classics",
        author="Brant Parker and Johnny Hart",
        earliest_date=date(2014, 11, 17)  # Classics reprint series
    ),
    ComicDefinition(
        name="pearlsbeforeswine",
        display_name="Pearls before Swine",
        base_url="https://www.gocomics.com/pearlsbeforeswine",
        author="Stephan Pastis",
        earliest_date=date(2002, 1, 7)  # Close to original start date
    ),
    ComicDefinition(
        name="shoe",
        display_name="Shoe",
        base_url="https://www.gocomics.com/shoe",
        author="Gary Brookins and Susie MacNelly",
        earliest_date=date(2001, 4, 8)  # Limited GoComics availability
    ),
    ComicDefinition(
        name="bc",
        display_name="B.C.",
        base_url="https://www.gocomics.com/bc",
        author="Johnny Hart",
        earliest_date=date(2002, 1, 1)  # Limited GoComics availability
    ),
    ComicDefinition(
        name="back-to-bc",
        display_name="Back to B.C.",
        base_url="https://www.gocomics.com/back-to-bc",
        author="Johnny Hart",
        earliest_date=date(2015, 9, 21)  # Recent reprint series
    ),
    ComicDefinition(
        name="pickles",
        display_name="Pickles",
        base_url="https://www.gocomics.com/pickles",
        author="Brian Crane",
        earliest_date=date(2003, 1, 1)  # Limited GoComics availability
    ),
    ComicDefinition(
        name="wumo",
        display_name="WuMo",
        base_url="https://www.gocomics.com/wumo",
        author="Mikael Wulff and Anders Morgenthaler",
        earliest_date=date(2013, 10, 13)  # Limited GoComics availability, with gaps
    ),
    ComicDefinition(
        name="speedbump",
        display_name="Speed Bump",
        base_url="https://www.gocomics.com/speedbump",
        author="Dave Coverly",
        earliest_date=date(2002, 1, 1)  # With gaps
    ),
    ComicDefinition(
        name="freerange",
        display_name="Free Range",
        base_url="https://www.gocomics.com/freerange",
        author="Bill Whitehead",
        earliest_date=date(2007, 2, 3) 
    ),
    ComicDefinition(
        name="offthemark",
        display_name="Off the Mark",
        base_url="https://www.gocomics.com/offthemark",
        author="Mark Parisi",
        earliest_date=date(2002, 9, 2)  # Limited GoComics availability
    ),
    ComicDefinition(
        name="mother-goose-and-grimm",
        display_name="Mother Goose and Grimm",
        base_url="https://www.gocomics.com/mother-goose-and-grimm",
        author="Mike Peters",
        earliest_date=date(1984, 10, 1)
    ),
    ComicDefinition(
        name="theflyingmccoys",
        display_name="The Flying McCoys",
        base_url="https://www.gocomics.com/theflyingmccoys",
        author="Gary McCoy and Glenn McCoy",
        earliest_date=date(2005, 5, 9)
    ),        
    ComicDefinition(
        name="duplex",
        display_name="The Duplex",
        base_url="https://www.gocomics.com/duplex",
        author="Glenn McCoy",
        earliest_date=date(1996, 8, 12)
    ),        
    ComicDefinition(
        name="realitycheck",
        display_name="Reality Check",
        base_url="https://www.gocomics.com/realitycheck",
        author="Dave Whamond",
        earliest_date=date(1997, 1, 1)
    ),    
    ComicDefinition(
        name="adamathome",
        display_name="Adam@Home",
        base_url="https://www.gocomics.com/adamathome",
        author="Rob Harrell",
        earliest_date=date(1995, 6, 20)
    ),
    ComicDefinition(
        name="ziggy",
        display_name="Ziggy",
        base_url="https://www.gocomics.com/ziggy",
        author="Tom Wilson & Tom II",
        earliest_date=date(1971, 6, 27)
    )        
]


def get_comic_definition(name: str) -> Optional[ComicDefinition]:
    """
    Get a comic definition by name.
    
    Args:
        name: The name of the comic to find
        
    Returns:
        ComicDefinition if found, None otherwise
    """
    for comic_def in COMIC_DEFINITIONS:
        if comic_def.name == name:
            return comic_def
    return None


def get_all_comic_names() -> list[str]:
    """
    Get a list of all available comic names.
    
    Returns:
        List of comic names
    """
    return [comic_def.name for comic_def in COMIC_DEFINITIONS]
