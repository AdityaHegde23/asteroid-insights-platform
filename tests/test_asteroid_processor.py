"""
Tests for the Asteroid Insights Platform ETL processor.

This module contains unit tests for the asteroid data processing functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.asteroid_processor import AsteroidProcessor
from src.nasa_api_client import NASAApiClient
from src.utils import calculate_risk_score, format_asteroid_data, validate_asteroid_data


class TestAsteroidProcessor:
    """Test cases for the AsteroidProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage_connection = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net"
        self.mock_sql_connection = "Driver={ODBC Driver 17 for SQL Server};Server=test.database.windows.net;Database=test;Uid=test;Pwd=test;"
        
        with patch('src.asteroid_processor.BlobServiceClient'):
            self.processor = AsteroidProcessor(
                storage_connection_string=self.mock_storage_connection,
                sql_connection_string=self.mock_sql_connection
            )
    
    def test_processor_initialization(self):
        """Test that the processor initializes correctly."""
        assert self.processor is not None
        assert self.processor.sql_connection_string == self.mock_sql_connection
    
    @patch('src.asteroid_processor.NASAApiClient')
    def test_fetch_asteroid_data(self, mock_nasa_client):
        """Test fetching asteroid data from NASA API."""
        # Mock NASA API response
        mock_response = {
            '2024-01-15': [
                {
                    'id': 2000433,
                    'name': '433 Eros',
                    'estimated_diameter': {
                        'kilometers': {
                            'estimated_diameter_min': 0.15,
                            'estimated_diameter_max': 0.34
                        }
                    },
                    'close_approach_data': [{
                        'miss_distance': {'kilometers': '50000000'},
                        'relative_velocity': {'kilometers_per_hour': '25000'}
                    }],
                    'is_potentially_hazardous_asteroid': False
                }
            ]
        }
        
        mock_nasa_client.return_value.get_near_earth_objects.return_value = mock_response
        
        result = self.processor.fetch_asteroid_data(days=1)
        
        assert len(result) == 1
        assert result[0]['name'] == '433 Eros'
        assert result[0]['id'] == 2000433
    
    def test_calculate_orbital_insights(self):
        """Test orbital insights calculation."""
        orbital_data = {
            'eccentricity': '0.15',
            'inclination': '10.5',
            'orbital_period': '365.25'
        }
        
        insights = self.processor._calculate_orbital_insights(orbital_data)
        
        assert insights['orbit_type'] == 'Low Eccentricity'
        assert insights['inclination_type'] == 'Medium Inclination'
        assert insights['orbital_period_days'] == 365.25
    
    def test_calculate_insights(self):
        """Test comprehensive insights calculation."""
        asteroid_data = {
            'id': 2000433,
            'name': '433 Eros',
            'estimated_diameter': {
                'kilometers': {
                    'estimated_diameter_max': 0.34
                }
            },
            'close_approach_data': [{
                'relative_velocity': {'kilometers_per_hour': 25000},
                'miss_distance': {'kilometers': 50000000},
                'close_approach_date': '2024-02-15'
            }],
            'orbital_data': {
                'eccentricity': 0.15,
                'inclination': 10.5
            },
            'risk_score': 0.3
        }
        
        insights = self.processor._calculate_insights(asteroid_data)
        
        assert insights['size_category'] == 'Medium (100m - 1km)'
        assert insights['orbit_type'] == 'Low Eccentricity'
        assert insights['velocity_category'] == 'Slow'
        assert insights['distance_category'] == 'Far'
        assert insights['threat_level'] == 'LOW'
        assert insights['is_high_priority'] is False


class TestNASAApiClient:
    """Test cases for the NASA API client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = NASAApiClient(api_key="test_key")
    
    @patch('requests.get')
    def test_make_request(self, mock_get):
        """Test making requests to NASA API."""
        mock_response = Mock()
        mock_response.json.return_value = {'test': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client._make_request('feed', {'start_date': '2024-01-15'})
        
        assert result == {'test': 'data'}
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_near_earth_objects(self, mock_get):
        """Test fetching near Earth objects."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'near_earth_objects': {
                '2024-01-15': [{'id': 1, 'name': 'Test Asteroid'}]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client.get_near_earth_objects(days=1)
        
        assert '2024-01-15' in result
        assert len(result['2024-01-15']) == 1
        assert result['2024-01-15'][0]['name'] == 'Test Asteroid'


class TestUtils:
    """Test cases for utility functions."""
    
    def test_calculate_risk_score(self):
        """Test risk score calculation."""
        diameter_data = {
            'kilometers': {
                'estimated_diameter_max': 0.5
            }
        }
        miss_distance = {'kilometers': '500000'}
        velocity = {'kilometers_per_hour': '30000'}
        
        risk_score = calculate_risk_score(diameter_data, miss_distance, velocity)
        
        assert 0.0 <= risk_score <= 1.0
        assert risk_score > 0.0  # Should be positive for this data
    
    def test_calculate_risk_score_invalid_data(self):
        """Test risk score calculation with invalid data."""
        diameter_data = {}
        miss_distance = {}
        velocity = {}
        
        risk_score = calculate_risk_score(diameter_data, miss_distance, velocity)
        
        assert risk_score == 0.0  # Should return 0 for invalid data
    
    def test_format_asteroid_data(self):
        """Test asteroid data formatting."""
        raw_data = {
            'id': 2000433,
            'name': '433 Eros',
            'nasa_jpl_url': 'http://test.com',
            'estimated_diameter': {'kilometers': {'estimated_diameter_max': 0.34}},
            'close_approach_data': [{
                'miss_distance': {'kilometers': '50000000'},
                'relative_velocity': {'kilometers_per_hour': '25000'}
            }]
        }
        
        formatted = format_asteroid_data(raw_data)
        
        assert formatted['id'] == 2000433
        assert formatted['name'] == '433 Eros'
        assert 'estimated_diameter' in formatted
        assert 'close_approach_data' in formatted
    
    def test_validate_asteroid_data_valid(self):
        """Test asteroid data validation with valid data."""
        valid_data = {
            'id': 2000433,
            'name': '433 Eros',
            'estimated_diameter': {'kilometers': {'estimated_diameter_max': 0.34}},
            'close_approach_data': []
        }
        
        assert validate_asteroid_data(valid_data) is True
    
    def test_validate_asteroid_data_invalid(self):
        """Test asteroid data validation with invalid data."""
        invalid_data = {
            'name': '433 Eros',  # Missing 'id'
            'estimated_diameter': 'not_a_dict'  # Wrong type
        }
        
        assert validate_asteroid_data(invalid_data) is False


class TestIntegration:
    """Integration tests for the complete pipeline."""
    
    @patch('src.asteroid_processor.BlobServiceClient')
    @patch('src.asteroid_processor.pyodbc.connect')
    def test_end_to_end_processing(self, mock_sql_connect, mock_blob_client):
        """Test end-to-end data processing."""
        # Mock SQL connection
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_sql_connect.return_value = mock_connection
        
        # Mock blob client
        mock_container = Mock()
        mock_blob = Mock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob
        
        processor = AsteroidProcessor(
            storage_connection_string="test_storage",
            sql_connection_string="test_sql"
        )
        
        # Mock NASA API response
        with patch.object(processor.nasa_client, 'get_near_earth_objects') as mock_nasa:
            mock_nasa.return_value = {
                '2024-01-15': [{
                    'id': 2000433,
                    'name': '433 Eros',
                    'estimated_diameter': {
                        'kilometers': {
                            'estimated_diameter_min': 0.15,
                            'estimated_diameter_max': 0.34
                        }
                    },
                    'close_approach_data': [{
                        'miss_distance': {'kilometers': '50000000'},
                        'relative_velocity': {'kilometers_per_hour': '25000'},
                        'close_approach_date': '2024-01-15'
                    }],
                    'is_potentially_hazardous_asteroid': False,
                    'orbital_data': {
                        'eccentricity': 0.15,
                        'inclination': 10.5
                    }
                }]
            }
            
            # Test the complete processing
            processor.process_data(mode='auto')
            
            # Verify SQL operations were called
            assert mock_cursor.execute.called
            assert mock_connection.commit.called


if __name__ == "__main__":
    pytest.main([__file__]) 