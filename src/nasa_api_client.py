"""
NASA API Client for fetching asteroid data from NASA's Near Earth Object API.

This module provides a clean interface to NASA's NEO API for retrieving
asteroid data and orbital parameters.
"""

import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NASAApiClient:
    """Client for interacting with NASA's Near Earth Object API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the NASA API client.
        
        Args:
            api_key: NASA API key (optional, will use environment variable if not provided)
        """
        self.api_key = api_key or os.getenv('NASA_API_KEY')
        self.base_url = 'https://api.nasa.gov/neo/rest/v1'
        
        if not self.api_key:
            logger.warning("No NASA API key provided. Some endpoints may be rate-limited.")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the NASA API.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters
            
        Returns:
            API response as dictionary
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Add API key if available
        if self.api_key:
            params = params or {}
            params['api_key'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"NASA API request failed: {e}")
            raise
    
    def get_near_earth_objects(self, days: int = 7) -> Dict[str, List[Dict]]:
        """Get near Earth objects for the specified number of days.
        
        Args:
            days: Number of days to fetch data for (max 7 days per request)
            
        Returns:
            Dictionary with dates as keys and lists of asteroid data as values
        """
        logger.info(f"Fetching NEO data for {days} days")
        
        # NASA API limits to 7 days per request
        if days > 7:
            logger.warning(f"Days parameter ({days}) exceeds API limit. Using 7 days.")
            days = 7
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days-1)
        
        params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        try:
            response = self._make_request('feed', params)
            
            # Extract and process the data
            neo_data = {}
            for date, asteroids in response.get('near_earth_objects', {}).items():
                neo_data[date] = asteroids
            
            logger.info(f"Successfully retrieved NEO data for {len(neo_data)} dates")
            return neo_data
            
        except Exception as e:
            logger.error(f"Failed to fetch NEO data: {e}")
            raise
    
    def get_asteroid_details(self, asteroid_id: str) -> Dict:
        """Get detailed information about a specific asteroid.
        
        Args:
            asteroid_id: NASA asteroid ID
            
        Returns:
            Detailed asteroid information
        """
        logger.info(f"Fetching details for asteroid {asteroid_id}")
        
        try:
            response = self._make_request(f'neo/{asteroid_id}')
            logger.info(f"Successfully retrieved details for asteroid {asteroid_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to fetch asteroid details: {e}")
            raise
    
    def get_asteroid_browse(self, page: int = 0, size: int = 20) -> Dict:
        """Browse asteroids with pagination.
        
        Args:
            page: Page number (0-based)
            size: Number of asteroids per page (max 20)
            
        Returns:
            Paginated asteroid data
        """
        logger.info(f"Browsing asteroids - page {page}, size {size}")
        
        params = {
            'page': page,
            'size': min(size, 20)  # API limit is 20
        }
        
        try:
            response = self._make_request('browse', params)
            logger.info(f"Successfully retrieved asteroid browse data")
            return response
        except Exception as e:
            logger.error(f"Failed to browse asteroids: {e}")
            raise
    
    def get_asteroid_stats(self) -> Dict:
        """Get statistics about near Earth objects.
        
        Returns:
            NEO statistics
        """
        logger.info("Fetching NEO statistics")
        
        try:
            response = self._make_request('stats')
            logger.info("Successfully retrieved NEO statistics")
            return response
        except Exception as e:
            logger.error(f"Failed to fetch NEO statistics: {e}")
            raise
    
    def search_asteroids(self, query: str) -> Dict:
        """Search for asteroids by name or designation.
        
        Args:
            query: Search query (asteroid name or designation)
            
        Returns:
            Search results
        """
        logger.info(f"Searching for asteroids with query: {query}")
        
        params = {'query': query}
        
        try:
            response = self._make_request('search', params)
            logger.info(f"Successfully retrieved search results for '{query}'")
            return response
        except Exception as e:
            logger.error(f"Failed to search asteroids: {e}")
            raise
    
    def get_asteroid_lookup(self, asteroid_id: str) -> Dict:
        """Look up asteroid by NASA ID.
        
        Args:
            asteroid_id: NASA asteroid ID
            
        Returns:
            Asteroid lookup data
        """
        logger.info(f"Looking up asteroid {asteroid_id}")
        
        try:
            response = self._make_request(f'lookup/{asteroid_id}')
            logger.info(f"Successfully retrieved lookup data for asteroid {asteroid_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to lookup asteroid: {e}")
            raise


def main():
    """Test the NASA API client."""
    import json
    
    client = NASAApiClient()
    
    try:
        # Test basic functionality
        print("Testing NASA API Client...")
        
        # Get NEO data for last 3 days
        neo_data = client.get_near_earth_objects(3)
        print(f"Retrieved NEO data for {len(neo_data)} dates")
        
        # Get statistics
        stats = client.get_asteroid_stats()
        print(f"Total NEOs: {stats.get('near_earth_object_count', 'N/A')}")
        
        # Browse asteroids
        browse = client.get_asteroid_browse(page=0, size=5)
        print(f"Browsed {len(browse.get('near_earth_objects', []))} asteroids")
        
    except Exception as e:
        print(f"Error testing NASA API client: {e}")


if __name__ == "__main__":
    main()
