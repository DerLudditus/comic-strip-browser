"""
Configuration management system for the comic strip browser application.

This module provides the ConfigManager class that handles JSON configuration
file I/O, including saving and loading comic start dates and other application
settings.
"""

import json
import os
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Any
from models.data_models import COMIC_DEFINITIONS


class ConfigManager:
    """
    Manages application configuration including comic start dates and settings.
    
    This class handles reading and writing configuration data to a JSON file,
    with a focus on storing the earliest available dates for each comic strip
    to avoid repeated discovery processes.
    """
    
    def __init__(self, config_file_path: str = "config.json"):
        """
        Initialize the ConfigManager with a configuration file path.
        
        Args:
            config_file_path: Path to the configuration JSON file
        """
        self.config_file_path = Path(config_file_path)
        self._config_data: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """
        Load configuration from the JSON file.
        
        If the file doesn't exist, creates a default configuration structure.
        """
        if self.config_file_path.exists():
            try:
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file {self.config_file_path}: {e}")
                self._config_data = self._create_default_config()
        else:
            self._config_data = self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """
        Create the default configuration structure with all 15 comic base URLs and hard-coded start dates.
        
        Returns:
            Dictionary containing the default configuration
        """
        config = {
            "version": "1.0",
            "comics": {},
            "start_dates": {},
            "settings": {
                "cache_size_per_comic": 200,
                "default_comic": "garfield",
                "auto_discover_dates": False  # No longer needed with hard-coded dates
            }
        }
        
        # Add all comic definitions to the configuration
        for comic_def in COMIC_DEFINITIONS:
            config["comics"][comic_def.name] = {
                "display_name": comic_def.display_name,
                "base_url": comic_def.base_url,
                "author": comic_def.author
            }
            
            # Add hard-coded start dates
            if comic_def.earliest_date:
                config["start_dates"][comic_def.name] = comic_def.earliest_date.isoformat()
        
        return config
    
    def _save_config(self) -> None:
        """
        Save the current configuration to the JSON file.
        
        Raises:
            IOError: If the file cannot be written
        """
        try:
            # Ensure the directory exists
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=2, default=self._json_serializer)
        except IOError as e:
            raise IOError(f"Could not save config file {self.config_file_path}: {e}")
    
    def _json_serializer(self, obj: Any) -> str:
        """
        Custom JSON serializer for date objects.
        
        Args:
            obj: Object to serialize
            
        Returns:
            String representation of the object
        """
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def save_start_dates(self, comic_dates_dict: Dict[str, date]) -> None:
        """
        Save comic start dates to the configuration.
        
        Args:
            comic_dates_dict: Dictionary mapping comic names to their earliest dates
        """
        if not isinstance(comic_dates_dict, dict):
            raise ValueError("comic_dates_dict must be a dictionary")
        
        # Validate that all comic names are valid
        valid_comic_names = {comic_def.name for comic_def in COMIC_DEFINITIONS}
        for comic_name in comic_dates_dict.keys():
            if comic_name not in valid_comic_names:
                raise ValueError(f"Invalid comic name: {comic_name}")
        
        # Convert dates to ISO format strings for JSON storage
        start_dates = {}
        for comic_name, start_date in comic_dates_dict.items():
            if not isinstance(start_date, date):
                raise ValueError(f"Start date for {comic_name} must be a date object")
            start_dates[comic_name] = start_date.isoformat()
        
        self._config_data["start_dates"] = start_dates
        self._save_config()
    
    def load_start_dates(self) -> Dict[str, date]:
        """
        Load comic start dates from the configuration.
        
        Returns:
            Dictionary mapping comic names to their earliest dates
        """
        start_dates = {}
        config_start_dates = self._config_data.get("start_dates", {})
        
        for comic_name, date_str in config_start_dates.items():
            try:
                start_dates[comic_name] = date.fromisoformat(date_str)
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid date format for {comic_name}: {date_str} ({e})")
        
        return start_dates
    
    def get_start_date(self, comic_name: str) -> Optional[date]:
        """
        Get the start date for a specific comic.
        
        Args:
            comic_name: Name of the comic
            
        Returns:
            Start date if available, None otherwise
        """
        start_dates = self.load_start_dates()
        return start_dates.get(comic_name)
    
    def set_start_date(self, comic_name: str, start_date: date) -> None:
        """
        Set the start date for a specific comic.
        
        Args:
            comic_name: Name of the comic
            start_date: Earliest available date for the comic
        """
        if not isinstance(start_date, date):
            raise ValueError("start_date must be a date object")
        
        # Validate comic name
        valid_comic_names = {comic_def.name for comic_def in COMIC_DEFINITIONS}
        if comic_name not in valid_comic_names:
            raise ValueError(f"Invalid comic name: {comic_name}")
        
        # Load existing start dates and update
        start_dates = self.load_start_dates()
        start_dates[comic_name] = start_date
        self.save_start_dates(start_dates)
    
    def has_all_start_dates(self) -> bool:
        """
        Check if start dates are available for all 15 comics.
        
        Returns:
            True if all comics have start dates, False otherwise
        """
        start_dates = self.load_start_dates()
        expected_comic_names = {comic_def.name for comic_def in COMIC_DEFINITIONS}
        return expected_comic_names.issubset(set(start_dates.keys()))
    
    def get_comic_base_url(self, comic_name: str) -> Optional[str]:
        """
        Get the base URL for a specific comic.
        
        Args:
            comic_name: Name of the comic
            
        Returns:
            Base URL if available, None otherwise
        """
        comic_config = self._config_data.get("comics", {}).get(comic_name, {})
        return comic_config.get("base_url")
    
    def get_all_comic_configs(self) -> Dict[str, Dict[str, str]]:
        """
        Get configuration for all comics.
        
        Returns:
            Dictionary mapping comic names to their configuration
        """
        return self._config_data.get("comics", {})
    
    def update_config(self, key: str, value: Any) -> None:
        """
        Update a configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: New value
        """
        keys = key.split('.')
        config_section = self._config_data
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config_section:
                config_section[k] = {}
            config_section = config_section[k]
        
        # Set the value
        config_section[keys[-1]] = value
        self._save_config()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        config_section = self._config_data
        
        try:
            for k in keys:
                config_section = config_section[k]
            return config_section
        except (KeyError, TypeError):
            return default
    
    def reset_config(self) -> None:
        """
        Reset configuration to default values.
        """
        self._config_data = self._create_default_config()
        self._save_config()
    
    def get_config_file_path(self) -> Path:
        """
        Get the path to the configuration file.
        
        Returns:
            Path object for the configuration file
        """
        return self.config_file_path
