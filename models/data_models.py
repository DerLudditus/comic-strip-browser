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
    daily_since_no_sundays: Optional[date] = None
    dates_one_off: Optional[tuple] = None
    weekly_between: Optional[tuple] = None
    daily_between: Optional[tuple] = None
    skip_ranges: Optional[List[Tuple[str, str]]] = None
    skip_days: Optional[tuple] = None
    never_scale_up: bool = False
    
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

        # Check skip_days
        if self.skip_days:
            check_iso = check_date.isoformat()
            if isinstance(self.skip_days, str):
                if check_iso == self.skip_days:
                    return False
            elif check_iso in self.skip_days:
                return False

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
            
        # daily_since_no_sundays (exclude Sundays if before daily_since)
        if self.daily_since_no_sundays and check_date >= self.daily_since_no_sundays:
            # If we haven't reached the "full daily" start date yet, skip Sundays
            if self.daily_since and check_date < self.daily_since:
                if check_date.weekday() == 6: # Sunday
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
            self.daily_since_no_sundays,
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


# Predefined comic definitions for the 42 supported comic strips
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
        name="animalcrackers",
        display_name="Animal Crackers @ GoComics",
        base_url="https://www.gocomics.com/animalcrackers",
        author="Mike Osbun",
        earliest_date=date(2001, 4, 8),
        info="On GoComics, Animal Crackers starts in April 2001 with one-offs on 8 and 15, then daily since 18.",
        dates_one_off=("2001-04-08", "2001-04-15"),
        daily_since=date(2001, 4, 18)
    ), 
    ComicDefinition(
        name="animal-crackers",
        display_name="Animal Crackers @ CK",
        base_url="https://comicskingdom.com/animal-crackers",
        author="Mike Osbun",
        earliest_date=date(2021, 5, 12),
        info="On Comics Kingdom, Animal Crackers has a much more limited availability than on GoComic: it starts on 2021-05-12."
    ),
    ComicDefinition(
        name="theargylesweater",
        display_name="The Argyle Sweater",
        base_url="https://www.gocomics.com/theargylesweater",
        author="Scott Hilburn",
        earliest_date=date(2006, 11, 29),
        info="The Argyle Sweater - on GoComics since 2006-11-29. Images are of questionable quality. They have improved since 2009-11-02 only to become (too) grainy."
    ),
    ComicDefinition(
        name="aunty-acid",
        display_name="Aunty Acid",
        base_url="https://www.gocomics.com/aunty-acid",
        author="Ged Backland",
        earliest_date=date(2013, 5, 6),
        info="Aunty Acid - on GoComics since 2013-05-06.",
        never_scale_up=True
    ),
    ComicDefinition(
        name="babyblues",
        display_name="Baby Blues",
        base_url="https://www.gocomics.com/babyblues",
        author="Rick Kirkman and Jerry Scott",
        earliest_date=date(1990, 1, 7),
        info="Baby Blues - on GoComics since 1990-01-07."
    ),    
    ComicDefinition(
        name="baldo",
        display_name="Baldo",
        base_url="https://www.gocomics.com/baldo",
        author="Hector D. Cantú and Carlos Castellanos",
        earliest_date=date(2000, 4, 17),
        info="Baldo - on GoComics since 2000-04-17.",
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
        info="On Comics Kingdom, Bizarro starts in 1996 irregularly (1996-02-18, 1996-03-03, 1996-03-31, 1996-04-07), then weekly since 1996-04-07 and daily since 2002-12-29.",
        dates_one_off=("1996-02-18", "1996-03-03", "1996-03-31", "1996-04-07"),
        weekly_between=("1996-04-07", "2002-12-22"),
        daily_since=date(2002, 12, 29)
    ),
    ComicDefinition(
        name="bliss",
        display_name="Bliss",
        base_url="https://www.gocomics.com/bliss",
        author="Harry Bliss",
        earliest_date=date(2004, 9, 1),
        dates_one_off=("2004-09-01",),
        daily_since=date(2008, 7, 28),
        info="Bliss - on GoComics since 2008-07-28, after a one-off on 2004-09-01."
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
        name="broomhilda",
        display_name="Broom Hilda",
        base_url="https://www.gocomics.com/broomhilda",
        author="Russell Myers",
        earliest_date=date(2001, 4, 8),
        dates_one_off=("2001-04-08","2001-04-15"),
        daily_since=date(2001, 4, 18),
        info="On GoComics, Broom Hilda starts in April 2001 with one-offs on 8 and 15, then daily since 18."
    ),       
    ComicDefinition(
        name="calvinandhobbes",
        display_name="Calvin and Hobbes",
        base_url="https://www.gocomics.com/calvinandhobbes",
        author="Bill Watterson",
        earliest_date=date(1985, 11, 18),
        info="Calvin and Hobbes - on GoComics since 1985-11-18. The original run ended on 1995-12-31. Reruns started on 2007-01-01. MIND THE GAP!",
        skip_ranges=(("1996-01-01", "2006-12-31"),)
    ),
    ComicDefinition(
        name="carpe-diem",
        display_name="Carpe Diem",
        base_url="https://comicskingdom.com/carpe-diem",
        author="Niklas Eriksson",
        earliest_date=date(2015, 5, 3),
        info="Carpe Diem - on Comics Kingdom since 2015-05-03."
    ), 
    ComicDefinition(
        name="crock",
        display_name="Crock",
        base_url="https://comicskingdom.com/crock",
        author="Bill Rechin",
        earliest_date=date(1996, 1, 7),
        info="On Comics Kingdom, Crock starts on 1996-01-07 initially on a weekly base, then daily since 1998-10-05.",
        weekly_between=("1996-01-07", "1998-10-04"),
        daily_since=date(1998, 10, 5)
    ),
    ComicDefinition(
        name="closetohome",
        display_name="Close to Home",
        base_url="https://www.gocomics.com/closetohome",
        author="John McPherson",
        earliest_date=date(1992, 12, 7),
        info="Close to Home - on GoComics since 1992-12-07."
    ), 
    ComicDefinition(
        name="day-by-dave",
        display_name="Day by Dave",
        base_url="https://www.gocomics.com/day-by-dave",
        author="Dave Whamond",
        earliest_date=date(2022, 12, 12),
        info="Day by Dave - on GoComics since 2022-12-12. Yeah, it's a recent comic. Also try Reality Check."
    ),         
    ComicDefinition(
        name="dennis-the-menace",
        display_name="Dennis The Menace",
        base_url="https://comicskingdom.com/dennis-the-menace",
        author="Ketcham, Hamilton & Ferdinand",
        earliest_date=date(1985, 12, 28),
        info="On Comics Kingdom, Dennis The Menace starts with a one-off on 1985-12-28, then on a weekly base since 1996-01-07, then daily since 1998-10-05.",
        dates_one_off=("1985-12-28",),
        weekly_between=("1996-01-07", "1998-10-04"),
        daily_since=date(1998, 10, 5)
    ),
    ComicDefinition(
        name="doonesbury",
        display_name="Doonesbury",
        base_url="https://www.gocomics.com/doonesbury",
        author="Garry Trudeau",
        earliest_date=date(1970, 10, 26),
        info="Doonesbury - on GoComics since 1970-10-26." 
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
        name="frazz",
        display_name="Frazz",
        base_url="https://www.gocomics.com/frazz",
        author="Jef Mallett",
        earliest_date=date(2001, 4, 2),
        info="Frazz - on GoComics since 2001-04-02." 
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
        name="thefuscobrothers",
        display_name="The Fusco Brothers",
        base_url="https://www.gocomics.com/thefuscobrothers",
        author="J.C. Duffy",
        earliest_date=date(1998, 1, 1),
        skip_days=("1998-01-18",),
        info="Free Range - on GoComics since 1998-01-01. Images before 2009-10-20 are of lower quality. Sundays became high-quality on 2010-07-25." 
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
        name="gingermeggs",
        display_name="Ginger Meggs",
        base_url="https://www.gocomics.com/gingermeggs",
        author="Jason Chatfield",
        earliest_date=date(2004, 4, 1),
        info="Ginger Meggs - on GoComics since 2004-04-01, with gaps. No Sundays until 2005-10-02. Many periods of poor-quality graphics that had stopped mid-2012.",
        daily_since_no_sundays=date(2004, 5, 3),
        daily_since=date(2005, 10, 2),
        dates_one_off=("2004-04-01", "2004-04-02", "2004-04-03", "2004-04-12", "2004-04-13", "2004-04-14", "2004-04-15"),
        skip_days=("2004-10-31",),        
        skip_ranges=(("2004-10-17", "2004-10-24"), ("2005-01-01", "2005-05-26"))
    ),     
   ComicDefinition(
        name="glasbergen-cartoons",
        display_name="Glasbergen Cartoons",
        base_url="https://www.gocomics.com/glasbergen-cartoons",
        author="Randy Glasbergen",
        earliest_date=date(2014, 7, 28),
        daily_since=date(2014, 7, 28),
        info="Glasbergen Cartoons - on GoComics AS REPRINTS since 2014-07-28, with plenty of random gaps! IMPORTANT: Known gaps are only marked in the calendar through May 3, 2026. Newer gaps will hit you as errors.",
        skip_ranges=(("2016-11-10","2016-11-14"), ("2016-12-04","2016-12-05"), ("2017-01-06","2017-01-08"), ("2017-02-25","2017-02-27"), ("2017-03-24","2017-03-27"), ("2017-05-20","2017-05-22"), ("2017-05-29","2017-05-31"), ("2018-11-14","2018-11-16"), ("2019-02-19","2019-03-18"), ("2019-05-14","2019-05-17"), ("2019-07-05","2019-07-07"), ("2019-07-24","2019-07-27"), ("2019-10-11","2019-10-13"), ("2019-10-22","2019-10-26"), ("2019-11-26","2019-11-28"), ("2019-12-02","2019-12-04"), ("2019-12-23","2019-12-27"), ("2020-01-21","2020-01-26"), ("2020-04-27","2020-04-30"), ("2020-05-01","2020-05-03"), ("2022-06-01","2022-06-15"), ("2022-08-02","2022-08-10"), ("2025-09-01","2025-09-07")),
        skip_days=("2014-08-29", "2016-12-13", "2017-01-13", "2017-01-20", "2017-01-21", "2017-01-25", "2017-01-27", "2017-01-32", "2017-02-07", "2017-02-16", "2017-02-22", "2017-02-23", "2017-03-09", "2017-03-11", "2017-03-12", "2017-03-14", "2017-03-16", "2017-03-19", "2017-03-29", "2017-04-01", "2017-04-05", "2017-04-06", "2017-04-17", "2017-04-19", "2017-04-24", "2017-04-28", "2017-05-02", "2017-05-15", "2017-06-13", "2017-07-17", "2017-07-22", "2017-08-06", "2017-09-14", "2017-10-02", "2017-10-21", "2017-10-22", "2017-11-01", "2017-11-08", "2017-11-14", "2017-11-15", "2017-11-22", "2017-12-01", "2017-12-11", "2017-12-17", "2017-12-20", "2018-02-17", "2018-03-13", "2018-03-31", "2018-04-06", "2018-04-09", "2018-06-02", "2018-06-10", "2018-06-20", "2018-06-23", "2018-06-26", "2018-06-29", "2018-06-30", "2018-07-29", "2018-08-02", "2018-08-03", "2018-08-12", "2018-08-14", "2018-08-22", "2018-08-25", "2018-09-03", "2018-09-05", "2018-09-10", "2018-09-19", "2018-09-24", "2018-10-20", "2018-12-07", "2018-12-08", "2019-04-02", "2019-04-03", "2019-04-07", "2019-04-08", "2019-04-11", "2019-04-12", "2019-08-30", "2019-09-17", "2019-10-05", "2019-12-09", "2019-12-29", "2020-01-06", "2020-01-07", "2020-03-04", "2020-03-05", "2020-03-31", "2020-04-01", "2020-04-02", "2020-04-07", "2020-09-09", "2020-09-25", "2020-09-26", "2020-10-11", "2020-11-01", "2020-11-02", "2020-11-10", "2021-03-03", "2021-08-04", "2021-06-06", "2022-08-15", "2022-10-02", "2022-10-06", "2022-10-23", "2022-11-16", "2022-12-11", "2022-12-18", "2022-12-20", "2023-07-01", "2023-07-07", "2023-10-26", "2023-10-27", "2024-10-08", "2025-03-10", "2025-06-06", "2025-07-17", "2025-07-18", "2025-08-02", "2025-08-07", "2025-08-09", "2025-08-13", "2025-08-20", "2025-09-16", "2025-09-20", "2025-10-12", "2025-10-19", "2025-12-03", "2025-12-20", "2025-12-21", "2025-12-26", "2026-01-01", "2026-02-23", "2026-03-07", "2026-03-16", "2026-03-17", "2026-04-25", "2026-04-26", "2026-05-02", "2026-05-03")
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
        name="lola",
        display_name="Lola",
        base_url="https://www.gocomics.com/lola",
        author="Todd Clark",
        earliest_date=date(2001, 4, 8),
        info="Lola - on GoComics since 2001-04-18 (after two one-offs on 8 and 15 of the same month).",
        dates_one_off=("2001-04-08","2001-04-15"),
        daily_since=date(2001, 4, 18)
    ),     
    ComicDefinition(
        name="marmaduke",
        display_name="Marmaduke",
        base_url="https://www.gocomi2004-10-24cs.com/marmaduke",
        author="Brad Anderson",
        earliest_date=date(1996, 12, 30),
        info="Marmaduke - on GoComics since 1996-12-30. No Sundays until 2011-06-05.",
        daily_since_no_sundays=date(1996, 12, 30),
        daily_since=date(2011, 6, 5),
        dates_one_off=("1997-01-19",),
        skip_days=("1997-01-16",),
        skip_ranges=(("1997-05-05", "1997-05-10"),)
    ),   
    ComicDefinition(
        name="marvin",
        display_name="Marvin",
        base_url="https://comicskingdom.com/marvin",
        author="Tom Armstrong",
        earliest_date=date(1996, 1, 7),
        info="On Comics Kingdom, Marvin starts on 1996-01-07 initially with a 2-week jump to 1996-01-21, then weekly, then daily since 1998-10-05.",
        dates_one_off=("1996-01-07",),
        weekly_between=("1996-01-21", "1998-10-04"),
        daily_since=date(1998, 10, 5)
    ),
    ComicDefinition(
        name="moderately-confused",
        display_name="Moderately Confused",
        base_url="https://www.gocomics.com/moderately-confused",
        author="Mike Peters",
        earliest_date=date(2003, 3, 3),
        never_on_sundays = "true",
        info="Moderately Confused - on GoComics since 2003-03-03."
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
        name="mutts",
        display_name="Mutts",
        base_url="https://comicskingdom.com/mutts",
        author="Patrick McDonnell",
        earliest_date=date(1994, 9, 11),
        info="On Comics Kingdom, Mutts starts on 1994-09-11 on a weekly base, then becomes daily on 1998-10-05.",
        weekly_between=("1994-09-11", "1998-10-04"),
        daily_since =date(1998, 10, 5)
    ),
    ComicDefinition(
        name="nonsequitur",
        display_name="Non Sequitur",
        base_url="https://www.gocomics.com/nonsequitur",
        author="Wiley Miller",
        earliest_date=date(1992, 2, 16),
        info="Non Sequitur - on GoComics since since 1992-02-16. Poor graphic quality before Jan. 1, 2002."
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
        name="theothercoast",
        display_name="The Other Coast",
        base_url="https://www.gocomics.com/theothercoast",
        author="Adrian Raeside",
        earliest_date=date(2002, 1, 1),
        info="Off the Mark - on GoComics since 2002-01-01 (limited availability). Occasional hiccups, then a Dec. 2003–Aug. 2009 period of reprints. New comics since Aug. 31, 2009. Color, high-quality images start on Nov. 2, 2009.",
        dates_one_off=("2002-01-01", "2002-01-02", "2002-01-03", "2002-01-04"),
        daily_since=date(2002, 8, 12),
        skip_ranges=(("2003-05-19", "2003-05-25"),),
        skip_days=("2002-08-18", "2002-10-27", "2002-11-03", "2002-11-24", "2003-01-11", "2003-04-06", "2003-06-01", "2003-06-08")
    ),  
    ComicDefinition(
        name="pardon-my-planet",
        display_name="Pardon My Planet",
        base_url="https://comicskingdom.com/pardon-my-planet",
        author="Vic Lee",
        earliest_date=date(1999, 12, 1),
        info="Pardon My Planet - on Comics Kingdom since 1999-12-01."
    ),     
    ComicDefinition(
        name="peanuts",
        display_name="Peanuts",
        base_url="https://www.gocomics.com/peanuts",
        author="Charles M. Schulz",
        earliest_date=date(1950, 10, 16),
        info="Peanuts - on GoComics since 1950-10-16.",
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
        name="pluggers2",
        display_name="Pluggers @ GoComics",
        base_url="https://www.gocomics.com/pluggers",
        author="Jeff MacNelly, Gary Brookins, Rick McKee",
        earliest_date=date(2001, 4, 8),
        info="On GoComics, Pluggers starts in April 2001 with comics on 8 and 15, then daily since 18 (limited availability).",
        dates_one_off=("2001-04-08","2001-04-15"),
        daily_since=date(2001, 4, 18)
    ),    
    ComicDefinition(
        name="pluggers",
        display_name="Pluggers @ CK",
        base_url="https://comicskingdom.com/pluggers",
        author="Jeff MacNelly, Gary Brookins, Rick McKee",
        earliest_date=date(2021, 11, 7),
        info="On Comics Kingdom, Pluggers starts on 2021-11-07 (extremely limited availability; it skips the Jeff MacNelly and Gary Brookins periods). Better colors than on GoComics."
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
