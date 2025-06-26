"""
Utility functions for the Asteroid Insights Platform.

This module contains helper functions for data processing, logging,
risk calculations, and other common operations.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests


def setup_logging(level: str = 'INFO', log_file: Optional[str] = None) -> None:
    """Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )


def calculate_risk_score(diameter_data: Dict, miss_distance: Dict, velocity: Dict) -> float:
    """Calculate risk score for an asteroid based on various factors.
    
    Args:
        diameter_data: Asteroid diameter information
        miss_distance: Miss distance information
        velocity: Relative velocity information
        
    Returns:
        Risk score between 0.0 and 1.0
    """
    try:
        # Extract values
        diameter_km = float(diameter_data.get('kilometers', {}).get('estimated_diameter_max', 0))
        miss_distance_km = float(miss_distance.get('kilometers', 0))
        velocity_kmh = float(velocity.get('kilometers_per_hour', 0))
        
        # Normalize factors (0-1 scale)
        # Diameter factor (larger = more dangerous)
        diameter_factor = min(diameter_km / 10.0, 1.0)  # Cap at 10km
        
        # Distance factor (closer = more dangerous)
        distance_factor = max(0, 1.0 - (miss_distance_km / 1000000.0))  # 1M km threshold
        
        # Velocity factor (faster = more dangerous)
        velocity_factor = min(velocity_kmh / 100000.0, 1.0)  # Cap at 100,000 km/h
        
        # Calculate weighted risk score
        risk_score = (
            diameter_factor * 0.4 +    # 40% weight
            distance_factor * 0.4 +    # 40% weight
            velocity_factor * 0.2      # 20% weight
        )
        
        return min(risk_score, 1.0)  # Ensure score doesn't exceed 1.0
        
    except (ValueError, KeyError, TypeError) as e:
        logging.warning(f"Error calculating risk score: {e}")
        return 0.0


def format_asteroid_data(asteroid: Dict) -> Dict:
    """Format and clean asteroid data for storage.
    
    Args:
        asteroid: Raw asteroid data from NASA API
        
    Returns:
        Formatted asteroid data
    """
    formatted = {
        'id': asteroid.get('id'),
        'name': asteroid.get('name'),
        'nasa_jpl_url': asteroid.get('nasa_jpl_url'),
        'absolute_magnitude_h': asteroid.get('absolute_magnitude_h'),
        'estimated_diameter': asteroid.get('estimated_diameter', {}),
        'is_potentially_hazardous_asteroid': asteroid.get('is_potentially_hazardous_asteroid', False),
        'close_approach_data': asteroid.get('close_approach_data', []),
        'orbital_data': asteroid.get('orbital_data', {}),
        'is_sentry_object': asteroid.get('is_sentry_object', False),
        'links': asteroid.get('links', {})
    }
    
    # Clean up close approach data
    if formatted['close_approach_data']:
        for approach in formatted['close_approach_data']:
            # Convert string values to appropriate types
            for key in ['miss_distance', 'relative_velocity']:
                if key in approach:
                    for unit, value in approach[key].items():
                        try:
                            approach[key][unit] = float(value.replace(',', ''))
                        except (ValueError, AttributeError):
                            pass
    
    return formatted


def validate_asteroid_data(asteroid: Dict) -> bool:
    """Validate asteroid data structure and required fields.
    
    Args:
        asteroid: Asteroid data to validate
        
    Returns:
        True if data is valid, False otherwise
    """
    required_fields = ['id', 'name', 'estimated_diameter']
    
    for field in required_fields:
        if field not in asteroid:
            logging.warning(f"Missing required field: {field}")
            return False
    
    # Validate estimated diameter structure
    diameter = asteroid.get('estimated_diameter', {})
    if not isinstance(diameter, dict):
        logging.warning("Invalid estimated_diameter structure")
        return False
    
    # Validate close approach data if present
    close_approach = asteroid.get('close_approach_data', [])
    if close_approach and not isinstance(close_approach, list):
        logging.warning("Invalid close_approach_data structure")
        return False
    
    return True


def generate_report_filename(prefix: str = 'asteroid_report', extension: str = 'json') -> str:
    """Generate a timestamped filename for reports.
    
    Args:
        prefix: Filename prefix
        extension: File extension
        
    Returns:
        Generated filename
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{prefix}_{timestamp}.{extension}"


def save_json_data(data: Any, filepath: str, indent: int = 2) -> bool:
    """Save data as JSON file.
    
    Args:
        data: Data to save
        filepath: Output file path
        indent: JSON indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
        logging.info(f"Data saved to {filepath}")
        return True
    except Exception as e:
        logging.error(f"Error saving data to {filepath}: {e}")
        return False


def load_json_data(filepath: str) -> Optional[Any]:
    """Load data from JSON file.
    
    Args:
        filepath: Input file path
        
    Returns:
        Loaded data or None if failed
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info(f"Data loaded from {filepath}")
        return data
    except Exception as e:
        logging.error(f"Error loading data from {filepath}: {e}")
        return None


def send_notification(webhook_url: str, message: str, title: str = "Asteroid Insights") -> bool:
    """Send notification via webhook (Teams, Slack, etc.).
    
    Args:
        webhook_url: Webhook URL for notification service
        message: Notification message
        title: Notification title
        
    Returns:
        True if successful, False otherwise
    """
    try:
        payload = {
            "title": title,
            "text": message,
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        logging.info("Notification sent successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error sending notification: {e}")
        return False


def get_environment_info() -> Dict[str, Union[str, Dict[str, str]]]:
    """Get information about the current environment.
    
    Returns:
        Dictionary with environment information
    """
    return {
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'platform': sys.platform,
        'working_directory': os.getcwd(),
        'timestamp': datetime.now().isoformat(),
        'environment_variables': {
            'NASA_API_KEY': 'SET' if os.getenv('NASA_API_KEY') else 'NOT_SET',
            'AZURE_STORAGE_CONNECTION_STRING': 'SET' if os.getenv('AZURE_STORAGE_CONNECTION_STRING') else 'NOT_SET',
            'AZURE_SQL_CONNECTION_STRING': 'SET' if os.getenv('AZURE_SQL_CONNECTION_STRING') else 'NOT_SET'
        }
    }


def format_size_bytes(size_bytes: int) -> str:
    """Format bytes into human-readable size.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def retry_on_failure(func, max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry function on failure.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Decorated function
    """
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logging.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
        
        raise last_exception
    
    return wrapper


def create_summary_statistics(asteroid_data: List[Dict]) -> Dict[str, Any]:
    """Create summary statistics from asteroid data.
    
    Args:
        asteroid_data: List of asteroid data dictionaries
        
    Returns:
        Dictionary with summary statistics
    """
    if not asteroid_data:
        return {'total_count': 0}
    
    stats = {
        'total_count': len(asteroid_data),
        'hazardous_count': sum(1 for a in asteroid_data if a.get('is_potentially_hazardous_asteroid', False)),
        'sentry_objects': sum(1 for a in asteroid_data if a.get('is_sentry_object', False)),
        'size_distribution': {},
        'hazard_level_distribution': {},
        'average_magnitude': 0.0,
        'closest_approach': None,
        'fastest_asteroid': None
    }
    
    # Calculate size distribution
    for asteroid in asteroid_data:
        diameter = asteroid.get('estimated_diameter', {}).get('kilometers', {}).get('estimated_diameter_max', 0)
        if diameter < 0.1:
            size_range = 'Small (< 100m)'
        elif diameter < 1:
            size_range = 'Medium (100m - 1km)'
        else:
            size_range = 'Large (> 1km)'
        stats['size_distribution'][size_range] = stats['size_distribution'].get(size_range, 0) + 1
    
    # Calculate hazard level distribution
    for asteroid in asteroid_data:
        hazard_level = asteroid.get('hazard_level', 'UNKNOWN')
        stats['hazard_level_distribution'][hazard_level] = stats['hazard_level_distribution'].get(hazard_level, 0) + 1
    
    # Calculate average magnitude
    magnitudes = [a.get('absolute_magnitude_h', 0) for a in asteroid_data if a.get('absolute_magnitude_h')]
    if magnitudes:
        stats['average_magnitude'] = sum(magnitudes) / len(magnitudes)
    
    # Find closest approach
    if asteroid_data:
        closest_asteroid = min(asteroid_data, 
                              key=lambda x: x.get('close_approach_data', [{}])[0].get('miss_distance', {}).get('kilometers', float('inf')))
        if closest_asteroid:
            stats['closest_approach'] = {
                'name': closest_asteroid.get('name'),
                'distance_km': closest_asteroid.get('close_approach_data', [{}])[0].get('miss_distance', {}).get('kilometers')
            }
    
    # Find fastest asteroid
    if asteroid_data:
        fastest_asteroid = max(asteroid_data,
                              key=lambda x: x.get('close_approach_data', [{}])[0].get('relative_velocity', {}).get('kilometers_per_hour', 0))
        if fastest_asteroid:
            stats['fastest_asteroid'] = {
                'name': fastest_asteroid.get('name'),
                'velocity_kmh': fastest_asteroid.get('close_approach_data', [{}])[0].get('relative_velocity', {}).get('kilometers_per_hour')
            }
    
    return stats


def validate_connection_strings() -> Dict[str, bool]:
    """Validate that required connection strings are set.
    
    Returns:
        Dictionary with validation results
    """
    required_vars = {
        'AZURE_STORAGE_CONNECTION_STRING': os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
        'AZURE_SQL_CONNECTION_STRING': os.getenv('AZURE_SQL_CONNECTION_STRING'),
        'NASA_API_KEY': os.getenv('NASA_API_KEY')
    }
    
    validation_results = {}
    for var_name, var_value in required_vars.items():
        validation_results[var_name] = var_value is not None and var_value.strip() != ''
    
    return validation_results


def log_processing_summary(asteroid_count: int, processing_time: float, mode: str):
    """Log a summary of the processing operation.
    
    Args:
        asteroid_count: Number of asteroids processed
        processing_time: Time taken for processing in seconds
        mode: Processing mode used
    """
    logging.info(f"Processing Summary:")
    logging.info(f"  Mode: {mode}")
    logging.info(f"  Asteroids processed: {asteroid_count}")
    logging.info(f"  Processing time: {processing_time:.2f} seconds")
    logging.info(f"  Average time per asteroid: {processing_time/asteroid_count:.3f} seconds" if asteroid_count > 0 else "  No asteroids processed")
