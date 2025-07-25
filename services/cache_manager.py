"""
Cache management system for the comic strip browser application.

This module implements an LRU (Least Recently Used) cache system that stores
comic data and images locally to improve performance and reduce network requests.
The cache maintains a maximum of 50 items per comic strip and handles both
metadata and image file storage.
"""

import os
import json
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests

from models.data_models import ComicData, CacheEntry
from services.error_handler import ErrorHandler, CacheError


class CacheManager:
    """
    Manages local caching of comic data and images with LRU eviction policy.
    
    The cache system stores comic metadata in JSON files and downloads images
    to local storage. Each comic strip maintains its own cache directory with
    a maximum of 50 entries. When the limit is exceeded, the least recently
    used entries are removed.
    """
    
    def __init__(self, cache_dir: str = "cache", error_handler: Optional[ErrorHandler] = None):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Base directory for cache storage
            error_handler: ErrorHandler instance for error management
        """
        self.cache_dir = Path(cache_dir)
        self.max_entries_per_comic = 50
        self.error_handler = error_handler or ErrorHandler()
        self._cache_index: Dict[str, Dict[str, CacheEntry]] = {}
        
        # Create cache directory structure
        try:
            self.cache_dir.mkdir(exist_ok=True)
            self._initialize_cache()
        except Exception as e:
            self.error_handler.handle_cache_error(e, "initialization", "all")
    
    def _initialize_cache(self) -> None:
        """Initialize cache by loading existing cache entries from disk."""
        for comic_dir in self.cache_dir.iterdir():
            if comic_dir.is_dir():
                comic_name = comic_dir.name
                self._cache_index[comic_name] = {}
                
                # Load cache index file if it exists
                index_file = comic_dir / "cache_index.json"
                if index_file.exists():
                    try:
                        with open(index_file, 'r') as f:
                            index_data = json.load(f)
                        
                        for date_str, entry_data in index_data.items():
                            cache_entry = self._deserialize_cache_entry(entry_data)
                            if cache_entry:
                                self._cache_index[comic_name][date_str] = cache_entry
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        print(f"Warning: Failed to load cache index for {comic_name}: {e}")
                        # Continue with empty cache for this comic
    
    def _get_comic_cache_dir(self, comic_name: str) -> Path:
        """Get the cache directory for a specific comic."""
        comic_dir = self.cache_dir / comic_name
        comic_dir.mkdir(exist_ok=True)
        return comic_dir
    
    def _get_date_key(self, date_obj: date) -> str:
        """Convert a date object to a string key for cache indexing."""
        return date_obj.strftime("%Y-%m-%d")
    
    def _get_image_filename(self, comic_data: ComicData) -> str:
        """Generate a filename for the cached image."""
        date_str = self._get_date_key(comic_data.date)
        extension = self._get_file_extension(comic_data.image_url, comic_data.image_format)
        return f"{date_str}.{extension}"
    
    def _get_file_extension(self, url: str, image_format: str) -> str:
        """Determine the file extension for an image."""
        # Try to get extension from URL first
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path and '.' in path:
            ext = path.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                return ext
        
        # Fall back to image format
        format_map = {
            'JPEG': 'jpg',
            'PNG': 'png',
            'GIF': 'gif',
            'WEBP': 'webp'
        }
        return format_map.get(image_format.upper(), 'jpg')
    
    def _download_image(self, image_url: str, target_path: Path) -> bool:
        """
        Download an image from URL to local storage.
        
        Args:
            image_url: URL of the image to download
            target_path: Local path where image should be saved
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            response = requests.get(image_url, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(target_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            
            return True
        except (requests.RequestException, IOError) as e:
            self.error_handler.handle_cache_error(e, "image download", str(target_path.parent.name))
            return False
    
    def _serialize_cache_entry(self, cache_entry: CacheEntry) -> dict:
        """Convert a CacheEntry to a JSON-serializable dictionary."""
        return {
            'comic_data': {
                'comic_name': cache_entry.comic_data.comic_name,
                'date': cache_entry.comic_data.date.isoformat(),
                'title': cache_entry.comic_data.title,
                'image_url': cache_entry.comic_data.image_url,
                'image_width': cache_entry.comic_data.image_width,
                'image_height': cache_entry.comic_data.image_height,
                'image_format': cache_entry.comic_data.image_format,
                'author': cache_entry.comic_data.author,
                'cached_image_path': cache_entry.comic_data.cached_image_path,
                'retrieved_at': cache_entry.comic_data.retrieved_at.isoformat()
            },
            'access_count': cache_entry.access_count,
            'last_accessed': cache_entry.last_accessed.isoformat(),
            'file_size': cache_entry.file_size
        }
    
    def _deserialize_cache_entry(self, entry_data: dict) -> Optional[CacheEntry]:
        """Convert a dictionary back to a CacheEntry object."""
        try:
            comic_data_dict = entry_data['comic_data']
            comic_data = ComicData(
                comic_name=comic_data_dict['comic_name'],
                date=date.fromisoformat(comic_data_dict['date']),
                title=comic_data_dict['title'],
                image_url=comic_data_dict['image_url'],
                image_width=comic_data_dict['image_width'],
                image_height=comic_data_dict['image_height'],
                image_format=comic_data_dict['image_format'],
                author=comic_data_dict['author'],
                cached_image_path=comic_data_dict.get('cached_image_path'),
                retrieved_at=datetime.fromisoformat(comic_data_dict['retrieved_at'])
            )
            
            return CacheEntry(
                comic_data=comic_data,
                access_count=entry_data['access_count'],
                last_accessed=datetime.fromisoformat(entry_data['last_accessed']),
                file_size=entry_data['file_size']
            )
        except (KeyError, ValueError, TypeError) as e:
            print(f"Failed to deserialize cache entry: {e}")
            return None
    
    def _save_cache_index(self, comic_name: str) -> None:
        """Save the cache index for a specific comic to disk."""
        comic_dir = self._get_comic_cache_dir(comic_name)
        index_file = comic_dir / "cache_index.json"
        
        if comic_name not in self._cache_index:
            return
        
        try:
            index_data = {}
            for date_key, cache_entry in self._cache_index[comic_name].items():
                index_data[date_key] = self._serialize_cache_entry(cache_entry)
            
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        except (IOError, json.JSONEncodeError) as e:
            print(f"Failed to save cache index for {comic_name}: {e}")
    
    def _cleanup_old_entries(self, comic_name: str) -> None:
        """Remove oldest cache entries when limit is exceeded."""
        if comic_name not in self._cache_index:
            return
        
        cache_entries = self._cache_index[comic_name]
        if len(cache_entries) <= self.max_entries_per_comic:
            return
        
        # Sort by last_accessed time (oldest first)
        sorted_entries = sorted(
            cache_entries.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest entries
        entries_to_remove = len(cache_entries) - self.max_entries_per_comic
        for i in range(entries_to_remove):
            date_key, cache_entry = sorted_entries[i]
            
            # Remove image file if it exists
            if cache_entry.comic_data.cached_image_path:
                image_path = Path(cache_entry.comic_data.cached_image_path)
                if image_path.exists():
                    try:
                        image_path.unlink()
                    except OSError as e:
                        print(f"Failed to remove cached image {image_path}: {e}")
            
            # Remove from cache index
            del self._cache_index[comic_name][date_key]
        
        # Save updated index
        self._save_cache_index(comic_name)
    
    def cache_comic(self, comic_data: ComicData) -> bool:
        """
        Cache a comic's data and image.
        
        Args:
            comic_data: Comic data to cache
            
        Returns:
            True if caching successful, False otherwise
        """
        comic_name = comic_data.comic_name
        date_key = self._get_date_key(comic_data.date)
        
        # Initialize comic cache if needed
        if comic_name not in self._cache_index:
            self._cache_index[comic_name] = {}
        
        # Download and cache the image
        comic_dir = self._get_comic_cache_dir(comic_name)
        image_filename = self._get_image_filename(comic_data)
        image_path = comic_dir / image_filename
        
        if not self._download_image(comic_data.image_url, image_path):
            return False
        
        # Update comic data with cached image path
        comic_data.cached_image_path = str(image_path)
        
        # Get file size
        try:
            file_size = image_path.stat().st_size
        except OSError:
            file_size = 0
        
        # Create cache entry
        cache_entry = CacheEntry(
            comic_data=comic_data,
            access_count=1,
            last_accessed=datetime.now(),
            file_size=file_size
        )
        
        # Store in cache index
        self._cache_index[comic_name][date_key] = cache_entry
        
        # Clean up old entries if needed
        self._cleanup_old_entries(comic_name)
        
        # Save cache index
        self._save_cache_index(comic_name)
        
        return True
    
    def get_cached_comic(self, comic_name: str, comic_date: date) -> Optional[ComicData]:
        """
        Retrieve a cached comic.
        
        Args:
            comic_name: Name of the comic strip
            comic_date: Date of the comic
            
        Returns:
            ComicData if found in cache, None otherwise
        """
        if comic_name not in self._cache_index:
            return None
        
        date_key = self._get_date_key(comic_date)
        if date_key not in self._cache_index[comic_name]:
            return None
        
        cache_entry = self._cache_index[comic_name][date_key]
        
        # Verify cached image still exists
        if cache_entry.comic_data.cached_image_path:
            image_path = Path(cache_entry.comic_data.cached_image_path)
            if not image_path.exists():
                # Image file is missing, remove from cache
                del self._cache_index[comic_name][date_key]
                self._save_cache_index(comic_name)
                return None
        
        # Update access information
        cache_entry.access_count += 1
        cache_entry.last_accessed = datetime.now()
        self._save_cache_index(comic_name)
        
        return cache_entry.comic_data
    
    def is_cached(self, comic_name: str, comic_date: date) -> bool:
        """
        Check if a comic is cached.
        
        Args:
            comic_name: Name of the comic strip
            comic_date: Date of the comic
            
        Returns:
            True if comic is cached, False otherwise
        """
        return self.get_cached_comic(comic_name, comic_date) is not None
    
    def get_cache_stats(self, comic_name: str) -> Dict[str, int]:
        """
        Get cache statistics for a specific comic.
        
        Args:
            comic_name: Name of the comic strip
            
        Returns:
            Dictionary with cache statistics
        """
        if comic_name not in self._cache_index:
            return {
                'total_entries': 0,
                'total_size': 0,
                'total_accesses': 0
            }
        
        cache_entries = self._cache_index[comic_name]
        total_size = sum(entry.file_size for entry in cache_entries.values())
        total_accesses = sum(entry.access_count for entry in cache_entries.values())
        
        return {
            'total_entries': len(cache_entries),
            'total_size': total_size,
            'total_accesses': total_accesses
        }
    
    def get_all_cache_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get cache statistics for all comics.
        
        Returns:
            Dictionary mapping comic names to their cache statistics
        """
        stats = {}
        for comic_name in self._cache_index.keys():
            stats[comic_name] = self.get_cache_stats(comic_name)
        return stats
    
    def clear_cache(self, comic_name: Optional[str] = None) -> None:
        """
        Clear cache for a specific comic or all comics.
        
        Args:
            comic_name: Name of comic to clear, or None to clear all
        """
        if comic_name:
            # Clear specific comic cache
            if comic_name in self._cache_index:
                comic_dir = self._get_comic_cache_dir(comic_name)
                
                # Remove all cached files
                for cache_entry in self._cache_index[comic_name].values():
                    if cache_entry.comic_data.cached_image_path:
                        image_path = Path(cache_entry.comic_data.cached_image_path)
                        if image_path.exists():
                            try:
                                image_path.unlink()
                            except OSError as e:
                                print(f"Failed to remove {image_path}: {e}")
                
                # Remove cache index file
                index_file = comic_dir / "cache_index.json"
                if index_file.exists():
                    try:
                        index_file.unlink()
                    except OSError as e:
                        print(f"Failed to remove cache index {index_file}: {e}")
                
                # Remove from memory
                del self._cache_index[comic_name]
                
                # Remove directory if empty
                try:
                    comic_dir.rmdir()
                except OSError:
                    pass  # Directory not empty or other error
        else:
            # Clear all caches
            for comic_name in list(self._cache_index.keys()):
                self.clear_cache(comic_name)
    
    def get_cached_dates(self, comic_name: str) -> List[date]:
        """
        Get list of cached dates for a specific comic.
        
        Args:
            comic_name: Name of the comic strip
            
        Returns:
            List of dates that are cached for this comic
        """
        if comic_name not in self._cache_index:
            return []
        
        dates = []
        for date_key in self._cache_index[comic_name].keys():
            try:
                comic_date = date.fromisoformat(date_key)
                dates.append(comic_date)
            except ValueError:
                continue
        
        return sorted(dates)