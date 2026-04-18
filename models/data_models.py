"""
Core data models for the comic strip browser application.

This module contains the dataclasses that represent comic data, comic definitions,
and cache entries used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Tuple


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
    scale: float = 1.0  # Per-comic display scale factor (1.0 = full size)
    
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
        
        if self.image_format is None:
            raise ValueError("image_format must be a string")
        
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
    info: str = ""
    normal_is_sundays: str = ""
    never_on_sundays: str = ""
    weekly_since: Optional[date] = None
    daily_since: Optional[date] = None
    dates_one_off: Optional[tuple] = None
    weekly_between: Optional[tuple] = None
    daily_between: Optional[tuple] = None
    skip_ranges: Optional[List[Tuple[str, str]]] = None
    scale: float = 1.0  # Display scale factor (1.0 = full size). Override for tall/wide comics.    
    
    def is_available(self, check_date: date) -> bool:
        """
        Check if the comic is available for a specific date based on complex rules.
        """
        if self.earliest_date and check_date < self.earliest_date:
            return False
        if check_date > date.today():
            return False
        
        # Check skip_ranges first (highest priority)
        if self.skip_ranges:
            for start_str, end_str in self.skip_ranges:
                try:
                    start = date.fromisoformat(start_str)
                    end = date.fromisoformat(end_str)
                    if start <= check_date <= end:
                        return False
                except (ValueError, TypeError):
                    continue

        # Check dates_one_off
        if self.dates_one_off:
            check_iso = check_date.isoformat()
            if isinstance(self.dates_one_off, str):
                if check_iso == self.dates_one_off:
                    return True
            elif check_iso in self.dates_one_off:
                return True

        # Check intervals
        # weekly_between
        if self.weekly_between and len(self.weekly_between) >= 2:
            try:
                start = date.fromisoformat(self.weekly_between[0])
                end = date.fromisoformat(self.weekly_between[1])
                if start <= check_date <= end:
                    return check_date.weekday() == 6  # Sunday
            except (ValueError, TypeError):
                pass
                
        # daily_between
        if self.daily_between and len(self.daily_between) >= 2:
            try:
                start = date.fromisoformat(self.daily_between[0])
                end = date.fromisoformat(self.daily_between[1])
                if start <= check_date <= end:
                    if self.never_on_sundays == "true" and check_date.weekday() == 6:
                        return False
                    return True
            except (ValueError, TypeError):
                pass
                
        # daily_since
        if self.daily_since and check_date >= self.daily_since:
            if self.never_on_sundays == "true" and check_date.weekday() == 6:
                return False
            return True
            
        # weekly_since
        if self.weekly_since and check_date >= self.weekly_since:
            return check_date.weekday() == 6

        # Determine if we have any intervals defined
        has_intervals = any([
            self.weekly_between, 
            self.daily_between, 
            self.daily_since, 
            self.weekly_since, 
            self.dates_one_off
        ])
        
        if not has_intervals:
            # Default behavior based on simple flags
            if self.normal_is_sundays == "true":
                return check_date.weekday() == 6
            if self.never_on_sundays == "true" and check_date.weekday() == 6:
                return False
            return True
        else:
            # If we have intervals/one-offs but none matched, it's a gap
            return False

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


# Predefined comic definitions for the 40 supported comic strips
# Earliest dates are hard-coded based on website availability
COMIC_DEFINITIONS = [
    ComicDefinition(
        name="adamathome",
        display_name="Adam@Home",
        base_url="https://www.gocomics.com/adamathome",
        author="Rob Harrell",
        earliest_date=date(1995, 6, 20),
        info="Adam@Home - on GoComics since 1995-06-20."
    ),
    ComicDefinition(
        name="andycapp",
        display_name="Andy Capp",
        base_url="https://www.gocomics.com/andycapp",
        author="Reg Smythe",
        earliest_date=date(2002, 1, 1),
        info="Andy Capp - on GoComics since 2002-01-01 (extremely limited availability)."
    ),    
    ComicDefinition(
        name="bc",
        display_name="B.C.",
        base_url="https://www.gocomics.com/bc",
        author="Johnny Hart",
        earliest_date=date(2002, 1, 1),
        info="B.C. - on GoComics since 2002-01-01 (extremely limited availability)."
    ),
    ComicDefinition(
        name="back-to-bc",
        display_name="Back to B.C.",
        base_url="https://www.gocomics.com/back-to-bc",
        author="Johnny Hart",
        earliest_date=date(2015, 9, 21),
        info="Back to B.C. - on GoComics since 2015-09-21 (recent reprint series)."
    ),
    ComicDefinition(
        name="beetle-bailey-1",
        display_name="Beetle Bailey",
        base_url="https://comicskingdom.com/beetle-bailey-1",
        author="Mort Walker",
        earliest_date=date(1996, 1, 7),
        info="On Comics Kingdom, Beetle Bailey starts on 1996-01-07 on a weekly base, then becomes daily on 1998-10-05.",
        weekly_between=("1996-01-07", "1998-10-04"),
        daily_since =date(1998, 10, 5)
    ),    
    ComicDefinition(
        name="bizarro",
        display_name="Bizarro",
        base_url="https://comicskingdom.com/bizarro",
        author="Wayno & Piraro",
        earliest_date=date(1996, 4, 7),
        scale=0.8,
        info="On Comics Kingdom, Bizarro starts in 1996 irregularly (1996-02-18, 1996-03-03, 1996-03-31, 1996-04-07), then weekly since 1996-04-07 and daily since 2002-12-29.",
        dates_one_off=("1996-02-18", "1996-03-03", "1996-03-31", "1996-04-07"),
        weekly_between=("1996-04-07", "2002-12-22"),
        daily_since=date(2002, 12, 29)
    ),     
    ComicDefinition(
        name="blondie",
        display_name="Blondie",
        base_url="https://comicskingdom.com/blondie",
        author="Dean Young & John Marshall",
        earliest_date=date(1970, 1, 1),
        info="Blondie - on Comics Kingdom since 1970-01-01 (extremely limited availability)." 
    ),     
    ComicDefinition(
        name="brilliant-mind-of-edison-lee",
        display_name="The Brilliant Mind Of Edison Lee",
        base_url="https://comicskingdom.com/brilliant-mind-of-edison-lee",
        author="John Hambrock",
        earliest_date=date(2006, 11, 12),
        info="The Brilliant Mind Of Edison Lee - on Comics Kingdom since 2006-11-12." 
    ),     
    ComicDefinition(
        name="calvinandhobbes",
        display_name="Calvin and Hobbes",
        base_url="https://www.gocomics.com/calvinandhobbes",
        author="Bill Watterson",
        earliest_date=date(1985, 11, 18),
        info="Calvin and Hobbes - on GoComics since 1985-11-18."
    ),
    ComicDefinition(
        name="carpe-diem",
        display_name="Carpe Diem",
        base_url="https://comicskingdom.com/carpe-diem",
        author="Niklas Eriksson",
        earliest_date=date(2015, 5, 3),
        scale=0.8,
        info="Carpe Diem - on Comics Kingdom since 2015-05-03."
    ),     
    ComicDefinition(
        name="crock",
        display_name="Crock",
        base_url="https://comicskingdom.com/crock",
        author="Bill Rechin",
        earliest_date=date(1996, 1, 7),
        scale=0.4,
        info="On Comics Kingdom, Crock starts on 1996-01-07 initially on a weekly base, then daily since 1998-10-05.",
        weekly_between=("1996-01-07", "1998-10-04"),
        daily_since=date(1998, 10, 5)
    ),     
    ComicDefinition(
        name="dennis-the-menace",
        display_name="Dennis The Menace",
        base_url="https://comicskingdom.com/dennis-the-menace",
        author="Ketcham, Hamilton & Ferdinand",
        earliest_date=date(1985, 12, 28),
        scale=0.8,
        info="On Comics Kingdom, Dennis The Menace starts with a one-off on 1985-12-28, then on a weekly base since 1996-01-07, then daily since 1998-10-05.",
        dates_one_off=("1985-12-28"),
        weekly_between=("1996-01-07", "1998-10-04"),
        daily_since=date(1998, 10, 5)
    ),     
    ComicDefinition(
        name="duplex",
        display_name="The Duplex",
        base_url="https://www.gocomics.com/duplex",
        author="Glenn McCoy",
        earliest_date=date(1996, 8, 12),
        info="The Duplex - on GoComics since 1996-08-12."
    ),    
    ComicDefinition(
        name="dustin",
        display_name="Dustin",
        base_url="https://comicskingdom.com/dustin",
        author="Steve Kelley & Jeff Parker",
        earliest_date=date(2010, 1, 4),
        info="Dustin - on Comics Kingdom since 2010-01-04." 
    ),     
    ComicDefinition(
        name="family-circus",
        display_name="The Family Circus",
        base_url="https://comicskingdom.com/family-circus",
        author="Bil & Jeff Keane",
        earliest_date=date(1996, 1, 7),
        scale=0.8,
        info="On Comics Kingdom, The Family Circus starts on 1996-01-07 initially on a weekly base, then daily since 1998-10-04.",
        weekly_between=("1996-01-07", "1998-10-04"),
        daily_since=date(1998, 10, 5)
    ),  
    ComicDefinition(
        name="theflyingmccoys",
        display_name="The Flying McCoys",
        base_url="https://www.gocomics.com/theflyingmccoys",
        author="Gary McCoy and Glenn McCoy",
        earliest_date=date(2005, 5, 9),
        info="The Flying McCoys - on GoComics since 2005-05-09."
    ),        
    ComicDefinition(
        name="foxtrot",
        display_name="Foxtrot",
        base_url="https://www.gocomics.com/foxtrot",
        author="Bill Amend",
        earliest_date=date(1988, 4, 11),
        info="Foxtrot - on GoComics since 1988-04-11. Daily until 2006-12-31. Weekly ON SUNDAYS since 2007-01-07.",
        normal_is_sundays="true",
        daily_between=("1988-04-11", "2006-12-31"),
        weekly_since =date(2007, 1, 7)
    ),          
    ComicDefinition(
        name="foxtrotclassics",
        display_name="Foxtrot Classics",
        base_url="https://www.gocomics.com/foxtrotclassics",
        author="Bill Amend",
        earliest_date=date(2007, 1, 1),
        info="Foxtrot Classics - on GoComics since 2007-01-01. Daily EXCEPT for Sundays, when you're supposed to read Foxtrot instead.",
        never_on_sundays = "true"
    ),      
    ComicDefinition(
        name="freerange",
        display_name="Free Range",
        base_url="https://www.gocomics.com/freerange",
        author="Bill Whitehead",
        earliest_date=date(2007, 2, 3),
        info="Free Range - on GoComics since 2007-02-03." 
    ),
    ComicDefinition(
        name="garfield",
        display_name="Garfield",
        base_url="https://www.gocomics.com/garfield",
        author="Jim Davis",
        earliest_date=date(1978, 6, 19),
        info="Garfield - on GoComics since 1978-06-19."
    ),    
    ComicDefinition(
        name="hagar-the-horrible",
        display_name="Hagar The Horrible",
        base_url="https://comicskingdom.com/hagar-the-horrible",
        author="Chris Browne",
        earliest_date=date(1975, 1, 1),
        info="On Comics Kingdom, Hagar The Horrible starts on 1975-01-01 (close enough to the original 1973-02-04 start date)." 
    ),     
    ComicDefinition(
        name="hi-and-lois",
        display_name="Hi and Lois",
        base_url="https://comicskingdom.com/hi-and-lois",
        author="Brian Walker, Greg Walker & Chance Browne",
        earliest_date=date(1996, 1, 7),
        info="On Comics Kingdom, Hi and Lois starts on 1996-01-07 initially on a weekly base, then daily since 1998-10-05.",
        weekly_between=("1996-01-07", "1998-10-04"),
        daily_since=date(1998, 10, 5)
    ), 
    ComicDefinition(
        name="marvin",
        display_name="Marvin",
        base_url="https://comicskingdom.com/marvin",
        author="Tom Armstrong",
        earliest_date=date(1996, 1, 7),
        info="On Comics Kingdom, Marvin starts on 1996-01-07 initially with a 2-week jump to 1996-01-21, then weekly, then daily since 1998-10-05.",
        dates_one_off=("1996-01-07"),
        weekly_between=("1996-01-21", "1998-10-04"),
        daily_since=date(1998, 10, 5)
    ),         
    ComicDefinition(
        name="mother-goose-and-grimm",
        display_name="Mother Goose and Grimm",
        base_url="https://www.gocomics.com/mother-goose-and-grimm",
        author="Mike Peters",
        earliest_date=date(1984, 10, 1),
        info="Mother Goose and Grimm - on GoComics since 2002-11-25 (limited availability)."
    ),
    ComicDefinition(
        name="offthemark",
        display_name="Off the Mark",
        base_url="https://www.gocomics.com/offthemark",
        author="Mark Parisi",
        earliest_date=date(2002, 9, 2),
        info="Off the Mark - on GoComics since 2002-09-02 (limited availability)."
    ),
    ComicDefinition(
        name="pardon-my-planet",
        display_name="Pardon My Planet",
        base_url="https://comicskingdom.com/pardon-my-planet",
        author="Vic Lee",
        earliest_date=date(1999, 12, 1),
        scale=0.8,
        info="Pardon My Planet - on Comics Kingdom since 1999-12-01."
    ),     
    ComicDefinition(
        name="peanuts",
        display_name="Peanuts",
        base_url="https://www.gocomics.com/peanuts",
        author="Charles M. Schulz",
        earliest_date=date(1950, 10, 16),
        info="Peanuts - on GoComics since 1950-10-16."
    ),
    ComicDefinition(
        name="peanuts-begins",
        display_name="Peanuts Begins",
        base_url="https://www.gocomics.com/peanuts-begins",
        author="Charles M. Schulz",
        earliest_date=date(1950, 10, 16),
        info="Peanuts Begins - on GoComics since 1950-10-16. HUGE GAPS! Not available: 1953-05-18 to 1954-04-19, and 1956-01-01 to 2022-04-16.",
        skip_ranges=(("1953-05-18", "1954-04-19"), ("1956-01-01", "2022-04-16"))
        
    ),
    ComicDefinition(
        name="pearlsbeforeswine",
        display_name="Pearls Before Swine",
        base_url="https://www.gocomics.com/pearlsbeforeswine",
        author="Stephan Pastis",
        earliest_date=date(2002, 1, 7),
        info="Pearls Before Swine - on GoComics since 2002-01-07 (close to original start date of 2001-12-31)."  
    ),
    ComicDefinition(
        name="pickles",
        display_name="Pickles",
        base_url="https://www.gocomics.com/pickles",
        author="Brian Crane",
        earliest_date=date(2003, 1, 1),
        info="Pickles - on GoComics since 2003-01-01 (extremely limited availability)."
    ),
    ComicDefinition(
        name="pluggers",
        display_name="Pluggers",
        base_url="https://comicskingdom.com/pluggers",
        author="Jeff MacNelly, Gary Brookins, Rick McKee",
        earliest_date=date(2021, 11, 7),
        scale=0.7,
        info="Pluggers - on Comics Kingdom since 2021-11-07 (extremely limited availability; it skips the Jeff MacNelly and Gary Brookins periods)."
    ),     
    ComicDefinition(
        name="realitycheck",
        display_name="Reality Check",
        base_url="https://www.gocomics.com/realitycheck",
        author="Dave Whamond",
        earliest_date=date(1997, 1, 1),
        info="Reality Check - on GoComics since 1997-01-01."
    ),
    ComicDefinition(
        name="rhymes-with-orange",
        display_name="Rhymes with Orange",
        base_url="https://comicskingdom.com/rhymes-with-orange",
        author="Hilary Price & Rina Piccolo",
        earliest_date=date(1995, 6, 19),
        info="Rhymes with Orange - on Comics Kingdom since 1995-06-19." 
    ),     
    ComicDefinition(
        name="shoe",
        display_name="Shoe @ GoComics",
        base_url="https://www.gocomics.com/shoe",
        author="Gary Brookins, Ben Lansing & Susie MacNelly",
        earliest_date=date(2001, 4, 8),
        info="Shoe - on GoComics since 2001-04-08 (extremely limited availability)."
    ),
    ComicDefinition(
        name="shoe2",
        display_name="Shoe @ CK",
        base_url="https://comicskingdom.com/shoe",
        author="Gary Brookins, Ben Lansing & Susie MacNelly",
        earliest_date=date(2006, 6, 19),
        info="Shoe - on Comics Kingdom since 2006-06-19 (extremely limited availability, even worse than on GoComics; colors differ)."
    ),
    ComicDefinition(
        name="speedbump",
        display_name="Speed Bump",
        base_url="https://www.gocomics.com/speedbump",
        author="Dave Coverly",
        earliest_date=date(2002, 1, 1),
        info="On GoComics, Speed Bump starts in Jan. 2002 irregularly (2002-01-01 to 2002-01-04), then daily since 2002-08-11.",
        dates_one_off=("2002-01-01", "2002-01-02", "2002-01-03", "2002-01-04"),
        daily_since=date(2002, 8, 11)
    ),  
    ComicDefinition(
        name="wizardofid",
        display_name="Wizard of Id",
        base_url="https://www.gocomics.com/wizardofid",
        author="Brant Parker and Johnny Hart",
        earliest_date=date(2002, 1, 1),
        info="Wizard of Id - on GoComics since 2002-01-01 (extremely limited availability)."
    ),
    ComicDefinition(
        name="wumo",
        display_name="WuMo",
        base_url="https://www.gocomics.com/wumo",
        author="Mikael Wulff and Anders Morgenthaler",
        earliest_date=date(2013, 10, 13),
        info="On GoComics, WuMo starts in Oct. 2013 irregularly (13, 20, 27), then daily since 2013-11-04.",
        dates_one_off=("2013-10-13", "2013-10-20", "2013-10-27"),
        daily_since=date(2013, 11, 4)        
    ),
    ComicDefinition(
        name="ziggy",
        display_name="Ziggy",
        base_url="https://www.gocomics.com/ziggy",
        author="Tom Wilson & Tom II",
        earliest_date=date(1971, 6, 27),
        info="Ziggy - since 1971-06-27."
    ),
    ComicDefinition(
        name="zits",
        display_name="Zits",
        base_url="https://comicskingdom.com/zits",
        author="Jerry Scott & Jim Borgman",
        earliest_date=date(1997, 7, 13),
        info="On Comics Kingdom, Zits starts on 1997-07-13 initially on a weekly base, then daily since 1998-10-05.",
        weekly_between=("1997-07-13", "1998-10-04"),
        daily_since=date(1998, 10, 5)        
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
