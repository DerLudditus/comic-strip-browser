"""
Enhanced logging service for the comic strip browser application.

This module provides comprehensive logging functionality with different log levels,
file rotation, error tracking, and debugging capabilities for UI error scenarios.
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import traceback
from enum import Enum


class LogLevel(Enum):
    """Log levels for different types of messages."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class UIErrorTracker:
    """
    Tracks UI-specific errors and user interactions for debugging.
    
    This class maintains a record of UI errors, user actions, and system state
    to help with debugging and improving error handling.
    """
    
    def __init__(self, max_entries: int = 250):
        """
        Initialize the UI error tracker.
        
        Args:
            max_entries: Maximum number of entries to keep in memory
        """
        self.max_entries = max_entries
        self.error_entries: List[Dict[str, Any]] = []
        self.user_action_entries: List[Dict[str, Any]] = []
        self.system_state_entries: List[Dict[str, Any]] = []
    
    def log_ui_error(self, error_type: str, error_message: str, component: str, 
                     recovery_actions: List[str] = None, user_data: Dict[str, Any] = None):
        """
        Log a UI error with context information.
        
        Args:
            error_type: Type of error (network, parsing, unavailable, etc.)
            error_message: Error message displayed to user
            component: UI component where error occurred
            recovery_actions: Available recovery actions
            user_data: Additional context data
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'ui_error',
            'error_type': error_type,
            'message': error_message,
            'component': component,
            'recovery_actions': recovery_actions or [],
            'user_data': user_data or {},
            'stack_trace': traceback.format_stack()[-5:]  # Last 5 stack frames
        }
        
        self._add_entry(self.error_entries, entry)
    
    def log_user_action(self, action: str, component: str, data: Dict[str, Any] = None):
        """
        Log a user action for debugging context.
        
        Args:
            action: Action performed by user
            component: UI component involved
            data: Additional action data
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'user_action',
            'action': action,
            'component': component,
            'data': data or {}
        }
        
        self._add_entry(self.user_action_entries, entry)
    
    def log_system_state(self, state_name: str, state_data: Dict[str, Any]):
        """
        Log system state for debugging.
        
        Args:
            state_name: Name of the state being logged
            state_data: State data
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'system_state',
            'state_name': state_name,
            'state_data': state_data
        }
        
        self._add_entry(self.system_state_entries, entry)
    
    def _add_entry(self, entry_list: List[Dict[str, Any]], entry: Dict[str, Any]):
        """Add entry to list with size limit."""
        entry_list.append(entry)
        if len(entry_list) > self.max_entries:
            entry_list.pop(0)
    
    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent error entries."""
        return self.error_entries[-count:]
    
    def get_recent_actions(self, count: int = 20) -> List[Dict[str, Any]]:
        """Get recent user action entries."""
        return self.user_action_entries[-count:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors for debugging."""
        error_types = {}
        components = {}
        
        for entry in self.error_entries:
            error_type = entry.get('error_type', 'unknown')
            component = entry.get('component', 'unknown')
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            components[component] = components.get(component, 0) + 1
        
        return {
            'total_errors': len(self.error_entries),
            'error_types': error_types,
            'affected_components': components,
            'recent_errors': self.get_recent_errors(5)
        }
    
    def export_debug_data(self, filepath: str):
        """Export all tracking data for debugging."""
        debug_data = {
            'export_timestamp': datetime.now().isoformat(),
            'error_entries': self.error_entries,
            'user_action_entries': self.user_action_entries,
            'system_state_entries': self.system_state_entries,
            'summary': self.get_error_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(debug_data, f, indent=2, default=str)


class LoggingService:
    """
    Enhanced logging service with file rotation, error tracking, and debugging.
    
    This service provides comprehensive logging functionality for the comic strip
    browser application, including specialized UI error tracking and debugging
    capabilities.
    """
    
    def __init__(self, log_dir: str = "logs", app_name: str = "comic_browser"):
        """
        Initialize the logging service.
        
        Args:
            log_dir: Directory for log files
            app_name: Application name for log files
        """
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.ui_error_tracker = UIErrorTracker()
        
        # Create log directory
        self.log_dir.mkdir(exist_ok=True)
        
        # Set up loggers
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Set up different loggers for various purposes."""
        # Main application logger
        self.app_logger = self._create_logger(
            'comic_browser',
            self.log_dir / f"{self.app_name}.log",
            LogLevel.INFO
        )
        
        # Error-specific logger
        self.error_logger = self._create_logger(
            'comic_browser.errors',
            self.log_dir / f"{self.app_name}_errors.log",
            LogLevel.ERROR
        )
        
        # UI-specific logger
        self.ui_logger = self._create_logger(
            'comic_browser.ui',
            self.log_dir / f"{self.app_name}_ui.log",
            LogLevel.DEBUG
        )
        
        # Network-specific logger
        self.network_logger = self._create_logger(
            'comic_browser.network',
            self.log_dir / f"{self.app_name}_network.log",
            LogLevel.DEBUG
        )
        
        # Performance logger
        self.performance_logger = self._create_logger(
            'comic_browser.performance',
            self.log_dir / f"{self.app_name}_performance.log",
            LogLevel.INFO
        )
    
    def _create_logger(self, name: str, log_file: Path, level: LogLevel) -> logging.Logger:
        """
        Create a logger with file rotation and console output.
        
        Args:
            name: Logger name
            log_file: Log file path
            level: Minimum log level
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(level.value)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(level.value)
        
        # Console handler for errors and above
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_ui_error(self, error_type: str, error_message: str, component: str,
                     recovery_actions: List[str] = None, user_data: Dict[str, Any] = None):
        """
        Log a UI error with enhanced tracking.
        
        Args:
            error_type: Type of error
            error_message: Error message
            component: UI component
            recovery_actions: Available recovery actions
            user_data: Additional context data
        """
        # Log to UI error tracker
        self.ui_error_tracker.log_ui_error(
            error_type, error_message, component, recovery_actions, user_data
        )
        
        # Log to appropriate loggers
        self.ui_logger.error(f"UI Error in {component}: {error_message} (Type: {error_type})")
        self.error_logger.error(f"UI Error: {error_message}")
        
        if recovery_actions:
            self.ui_logger.info(f"Recovery actions available: {', '.join(recovery_actions)}")
    
    def log_user_action(self, action: str, component: str, data: Dict[str, Any] = None):
        """
        Log user action for debugging context.
        
        Args:
            action: User action
            component: UI component
            data: Additional data
        """
        self.ui_error_tracker.log_user_action(action, component, data)
        self.ui_logger.debug(f"User action in {component}: {action}")
    
    def log_network_operation(self, operation: str, url: str, success: bool, 
                            duration_ms: float = None, error: str = None):
        """
        Log network operations for debugging.
        
        Args:
            operation: Type of network operation
            url: URL accessed
            success: Whether operation succeeded
            duration_ms: Operation duration in milliseconds
            error: Error message if failed
        """
        status = "SUCCESS" if success else "FAILED"
        message = f"Network {operation}: {url} - {status}"
        
        if duration_ms is not None:
            message += f" ({duration_ms:.1f}ms)"
        
        if error:
            message += f" - Error: {error}"
            self.network_logger.error(message)
            self.error_logger.error(f"Network error: {error}")
        else:
            self.network_logger.info(message)
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """
        Log performance metrics.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
        """
        self.performance_logger.info(f"Performance: {metric_name} = {value:.2f}{unit}")
    
    def log_system_state(self, state_name: str, state_data: Dict[str, Any]):
        """
        Log system state for debugging.
        
        Args:
            state_name: Name of the state
            state_data: State data
        """
        self.ui_error_tracker.log_system_state(state_name, state_data)
        self.app_logger.debug(f"System state '{state_name}': {state_data}")
    
    def get_logger(self, logger_type: str = "app") -> logging.Logger:
        """
        Get a specific logger instance.
        
        Args:
            logger_type: Type of logger (app, error, ui, network, performance)
            
        Returns:
            Logger instance
        """
        loggers = {
            'app': self.app_logger,
            'error': self.error_logger,
            'ui': self.ui_logger,
            'network': self.network_logger,
            'performance': self.performance_logger
        }
        
        return loggers.get(logger_type, self.app_logger)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of tracked errors."""
        return self.ui_error_tracker.get_error_summary()
    
    def export_debug_data(self, include_logs: bool = True) -> str:
        """
        Export debug data for troubleshooting.
        
        Args:
            include_logs: Whether to include recent log entries
            
        Returns:
            Path to exported debug file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = self.log_dir / f"debug_export_{timestamp}.json"
        
        # Export UI error tracker data
        self.ui_error_tracker.export_debug_data(debug_file)
        
        if include_logs:
            # Add recent log entries
            debug_data = {}
            with open(debug_file, 'r') as f:
                debug_data = json.load(f)
            
            # Add recent log entries from each log file
            debug_data['recent_logs'] = self._get_recent_log_entries()
            
            with open(debug_file, 'w') as f:
                json.dump(debug_data, f, indent=2, default=str)
        
        return str(debug_file)
    
    def _get_recent_log_entries(self, lines: int = 100) -> Dict[str, List[str]]:
        """Get recent log entries from all log files."""
        recent_logs = {}
        
        log_files = {
            'app': self.log_dir / f"{self.app_name}.log",
            'errors': self.log_dir / f"{self.app_name}_errors.log",
            'ui': self.log_dir / f"{self.app_name}_ui.log",
            'network': self.log_dir / f"{self.app_name}_network.log",
            'performance': self.log_dir / f"{self.app_name}_performance.log"
        }
        
        for log_type, log_file in log_files.items():
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        all_lines = f.readlines()
                        recent_logs[log_type] = all_lines[-lines:] if len(all_lines) > lines else all_lines
                except Exception as e:
                    recent_logs[log_type] = [f"Error reading log file: {e}"]
            else:
                recent_logs[log_type] = ["Log file not found"]
        
        return recent_logs
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Clean up old log files.
        
        Args:
            days_to_keep: Number of days of logs to keep
        """
        import time
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    self.app_logger.info(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    self.app_logger.warning(f"Failed to clean up log file {log_file}: {e}")


# Global logging service instance
_logging_service: Optional[LoggingService] = None


def get_logging_service() -> LoggingService:
    """Get the global logging service instance."""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service


def setup_logging(log_dir: str = "logs", app_name: str = "comic_browser") -> LoggingService:
    """
    Set up the global logging service.
    
    Args:
        log_dir: Directory for log files
        app_name: Application name
        
    Returns:
        Configured logging service
    """
    global _logging_service
    _logging_service = LoggingService(log_dir, app_name)
    return _logging_service
