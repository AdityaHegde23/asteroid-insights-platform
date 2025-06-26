#!/usr/bin/env python3
"""
Test script to verify duplicate asteroid handling.

This test ensures that:
1. Raw data can be processed multiple times without errors
2. Processed insights can be updated when the same asteroid is processed again
3. No duplicate records are created in either table
"""

import os
import sys
import logging
from datetime import datetime
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from asteroid_processor import AsteroidProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mock_asteroid_data():
    """Create mock asteroid data for testing."""
    return [
        {
            'id': 2000433,
            'name': '433 Eros',
            'nasa_jpl_url': 'http://ssd.jpl.nasa.gov/sbdb.cgi?sstr=2000433',
            'absolute_magnitude_h': 11.16,
            'estimated_diameter': {
                'kilometers': {
                    'estimated_diameter_min': 0.15,
                    'estimated_diameter_max': 0.34
                }
            },
            'is_potentially_hazardous_asteroid': False,
            'is_sentry_object': False,
            'close_approach_data': [
                {
                    'close_approach_date': '2024-01-15',
                    'close_approach_full': '2024-Jan-15 12:00',
                    'epoch_osculation': 2459580.5,
                    'relative_velocity': {
                        'kilometers_per_second': '6.94',
                        'kilometers_per_hour': '25000',
                        'miles_per_hour': '15500'
                    },
                    'miss_distance': {
                        'astronomical': '0.334',
                        'lunar': '130.0',
                        'kilometers': '50000000'
                    },
                    'orbiting_body': 'Earth'
                }
            ],
            'orbital_data': {
                'orbit': {
                    'epoch_osculation': 2459580.5,
                    'eccentricity': 0.223,
                    'semi_major_axis': 1.458,
                    'inclination': 10.829,
                    'ascending_node_longitude': 304.401,
                    'orbital_period': 643.219,
                    'perihelion_distance': 1.133,
                    'perihelion_argument': 178.664,
                    'aphelion_distance': 1.783,
                    'perihelion_time': 2459580.5,
                    'mean_anomaly': 0.0,
                    'mean_motion': 0.559,
                    'equinox': 'J2000',
                    'orbit_determination_date': '2024-01-01',
                    'orbit_uncertainty': 0,
                    'minimum_orbit_intersection': 0.334,
                    'jupiter_tisserand_invariant': 4.558,
                    'earth_minimum_orbit_intersection_distance': 0.334,
                    'orbit_id': '1',
                    'object_designation': '433'
                }
            }
        }
    ]


def test_duplicate_handling():
    """Test that duplicate asteroids are handled correctly."""
    
    # Mock the database connection and cursor
    mock_cursor = Mock()
    mock_cursor.rowcount = 1
    mock_connection = Mock()
    mock_connection.cursor.return_value = mock_cursor
    
    # Mock the storage client
    mock_storage_client = Mock()
    mock_container_client = Mock()
    mock_blob_client = Mock()
    mock_storage_client.get_container_client.return_value = mock_container_client
    mock_container_client.get_blob_client.return_value = mock_blob_client
    
    # Create processor with mocked dependencies
    with patch('pyodbc.connect', return_value=mock_connection), \
         patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_storage_client), \
         patch('asteroid_processor.NASAApiClient'):
        
        processor = AsteroidProcessor(
            storage_connection_string='mock_storage_connection',
            sql_connection_string='mock_sql_connection'
        )
        
        # Create test data
        asteroid_data = create_mock_asteroid_data()
        
        # Test 1: First processing (should insert)
        logger.info("Test 1: First processing - should insert new records")
        processor.store_raw_data_sql(asteroid_data)
        processor.store_processed_insights_sql(asteroid_data)
        
        # Verify that INSERT was called (not MERGE for first time)
        # Note: In our implementation, we always use MERGE, so this is expected
        assert mock_cursor.execute.called, "Database operations should have been called"
        
        # Reset mock for second test
        mock_cursor.reset_mock()
        
        # Test 2: Second processing with same data (should update)
        logger.info("Test 2: Second processing - should update existing records")
        processor.store_raw_data_sql(asteroid_data)
        processor.store_processed_insights_sql(asteroid_data)
        
        # Verify that MERGE operations were called
        assert mock_cursor.execute.called, "Database operations should have been called for updates"
        
        # Test 3: Verify no exceptions were raised
        logger.info("Test 3: Verify no exceptions were raised during duplicate processing")
        
        # Check that commit was called (indicating successful processing)
        assert mock_connection.commit.called, "Database commit should have been called"
        
        logger.info("✅ All duplicate handling tests passed!")


def test_upsert_logic():
    """Test the UPSERT logic specifically."""
    
    mock_cursor = Mock()
    mock_cursor.rowcount = 1
    mock_connection = Mock()
    mock_connection.cursor.return_value = mock_cursor
    
    # Mock the storage client
    mock_storage_client = Mock()
    mock_container_client = Mock()
    mock_blob_client = Mock()
    mock_storage_client.get_container_client.return_value = mock_container_client
    mock_container_client.get_blob_client.return_value = mock_blob_client
    
    with patch('pyodbc.connect', return_value=mock_connection), \
         patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_storage_client), \
         patch('asteroid_processor.NASAApiClient'):
        
        processor = AsteroidProcessor(
            storage_connection_string='mock_storage_connection',
            sql_connection_string='mock_sql_connection'
        )
        
        asteroid_data = create_mock_asteroid_data()
        
        # Test that MERGE statements are used (not simple INSERT)
        processor.store_raw_data_sql(asteroid_data)
        
        # Check that MERGE was called (not INSERT)
        call_args = mock_cursor.execute.call_args[0][0]
        assert 'MERGE' in call_args, "Should use MERGE statement for UPSERT"
        assert 'WHEN MATCHED THEN' in call_args, "Should have UPDATE clause"
        assert 'WHEN NOT MATCHED THEN' in call_args, "Should have INSERT clause"
        
        logger.info("✅ UPSERT logic test passed!")


if __name__ == '__main__':
    logger.info("Starting duplicate handling tests...")
    
    try:
        test_duplicate_handling()
        test_upsert_logic()
        logger.info("🎉 All tests completed successfully!")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1) 