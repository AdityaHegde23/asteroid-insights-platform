#!/usr/bin/env python3
"""
Asteroid Insights Platform - Main ETL Processor

This module processes asteroid data from NASA's API and stores insights
in Azure SQL Database. Raw data is stored in Azure Blob Storage.
"""
from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd
import pyodbc
import requests
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from tenacity import retry, stop_after_attempt, wait_exponential

from nasa_api_client import NASAApiClient
from utils import setup_logging, calculate_risk_score, format_asteroid_data, validate_asteroid_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsteroidProcessor:
    """Main class for processing asteroid data from NASA API to Azure SQL Database."""
    
    def __init__(self, 
                 storage_connection_string: str, 
                 sql_connection_string: str,
                 function_url: Optional[str] = None):
        """Initialize the asteroid processor.
        
        Args:
            storage_connection_string: Azure Storage connection string
            sql_connection_string: Azure SQL Database connection string
            function_url: Azure Function URL for additional processing
        """
        self.nasa_client = NASAApiClient()
        self.storage_client = BlobServiceClient.from_connection_string(storage_connection_string)
        self.sql_connection_string = sql_connection_string
        self.function_url = function_url
        
        # Validate that required containers exist
        self._validate_storage_containers()
    
    def _validate_storage_containers(self):
        """Validate that required blob containers exist.
        
        Raises:
            Exception: If required containers don't exist
        """
        required_containers = ['asteroid-raw']
        
        for container_name in required_containers:
            try:
                container_client = self.storage_client.get_container_client(container_name)
                container_client.get_container_properties()
                logger.info(f"Container {container_name} exists and is accessible")
            except Exception as e:
                logger.error(f"Container {container_name} does not exist or is not accessible: {e}")
                raise Exception(f"Required container '{container_name}' not found. Please deploy infrastructure first.")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def fetch_asteroid_data(self, days: int = 7) -> List[Dict]:
        """Fetch asteroid data from NASA API.
        
        Args:
            days: Number of days to fetch data for
            
        Returns:
            List of asteroid data dictionaries
        """
        logger.info(f"Fetching asteroid data for the last {days} days")
        
        try:
            # Get near Earth objects
            neo_data = self.nasa_client.get_near_earth_objects(days)
            
            # Process and enrich the data
            processed_data = []
            for date, asteroids in neo_data.items():
                for asteroid in asteroids:
                    enriched_asteroid = self._enrich_asteroid_data(asteroid, date)
                    processed_data.append(enriched_asteroid)
            
            logger.info(f"Successfully fetched {len(processed_data)} asteroid records")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching asteroid data: {e}")
            raise
    
    def _enrich_asteroid_data(self, asteroid: Dict, date: str) -> Dict:
        """Enrich asteroid data with additional calculations and insights.
        
        Args:
            asteroid: Raw asteroid data from NASA API
            date: Date of the asteroid data
            
        Returns:
            Enriched asteroid data
        """
        enriched = asteroid.copy()
        enriched['processed_date'] = datetime.now().isoformat()
        enriched['data_source'] = 'NASA NEO API'
        
        # Calculate risk score
        if 'close_approach_data' in asteroid and asteroid['close_approach_data']:
            approach_data = asteroid['close_approach_data'][0]
            enriched['risk_score'] = calculate_risk_score(
                asteroid['estimated_diameter'],
                approach_data['miss_distance'],
                approach_data['relative_velocity']
            )
            
            # Add hazard classification
            if enriched['risk_score'] > 0.7:
                enriched['hazard_level'] = 'HIGH'
            elif enriched['risk_score'] > 0.4:
                enriched['hazard_level'] = 'MEDIUM'
            else:
                enriched['hazard_level'] = 'LOW'
        
        # Add orbital insights
        if 'orbital_data' in asteroid:
            enriched['orbital_insights'] = self._calculate_orbital_insights(asteroid['orbital_data'])
        
        return enriched
    
    def _calculate_orbital_insights(self, orbital_data: Dict) -> Dict:
        """Calculate orbital insights for an asteroid.
        
        Args:
            orbital_data: Orbital parameters from NASA API
            
        Returns:
            Dictionary of orbital insights
        """
        insights = {}
        
        try:
            # Calculate orbital period
            if 'orbital_period' in orbital_data:
                insights['orbital_period_days'] = float(orbital_data['orbital_period'])
            
            # Calculate eccentricity classification
            if 'eccentricity' in orbital_data:
                ecc = float(orbital_data['eccentricity'])
                if ecc < 0.1:
                    insights['orbit_type'] = 'Nearly Circular'
                elif ecc < 0.3:
                    insights['orbit_type'] = 'Low Eccentricity'
                else:
                    insights['orbit_type'] = 'High Eccentricity'
            
            # Calculate inclination insights
            if 'inclination' in orbital_data:
                incl = float(orbital_data['inclination'])
                if incl < 5:
                    insights['inclination_type'] = 'Low Inclination'
                elif incl < 20:
                    insights['inclination_type'] = 'Medium Inclination'
                else:
                    insights['inclination_type'] = 'High Inclination'
                    
        except (ValueError, KeyError) as e:
            logger.warning(f"Error calculating orbital insights: {e}")
            insights['error'] = str(e)
        
        return insights
    
    def store_raw_data_blob(self, asteroid_data: List[Dict]):
        """Store raw asteroid data in Azure Blob Storage.
        
        Args:
            asteroid_data: List of asteroid data dictionaries
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"asteroid_data_{timestamp}.json"
        
        container_client = self.storage_client.get_container_client('asteroid-raw')
        blob_client = container_client.get_blob_client(filename)
        
        # Store as JSON - this is the raw NASA API response
        json_data = json.dumps(asteroid_data, indent=2, default=str)
        blob_client.upload_blob(json_data, overwrite=True)
        
        logger.info(f"Stored raw NASA API data in blob: {filename}")
    
    def _get_sql_connection(self):
        """Get SQL Database connection.
        
        Returns:
            pyodbc connection object
        """
        try:
            connection = pyodbc.connect(self.sql_connection_string)
            return connection
        except Exception as e:
            logger.error(f"Error connecting to SQL Database: {e}")
            raise
    
    def store_raw_data_sql(self, asteroid_data: List[Dict]):
        """Store raw asteroid data in Azure SQL Database.
        
        Args:
            asteroid_data: List of asteroid data dictionaries
        """
        connection = self._get_sql_connection()
        cursor = connection.cursor()
        
        try:
            for asteroid in asteroid_data:
                # Extract values for SQL insertion
                close_approach_data = asteroid.get('close_approach_data', [{}])[0] if asteroid.get('close_approach_data') else {}
                orbital_data = asteroid.get('orbital_data', {})
                
                # Prepare SQL insert statement
                sql = """
                INSERT INTO raw_asteroid_data (
                    id, name, nasa_jpl_url, absolute_magnitude_h,
                    estimated_diameter_min_km, estimated_diameter_max_km,
                    is_potentially_hazardous_asteroid, is_sentry_object,
                    close_approach_date, close_approach_full,
                    epoch_osculation, eccentricity, semi_major_axis, inclination,
                    ascending_node_longitude, orbital_period, perihelion_distance,
                    perihelion_argument, aphelion_distance, perihelion_time,
                    mean_anomaly, mean_motion, equinox, orbit_determination_date,
                    orbit_uncertainty, minimum_orbit_intersection,
                    jupiter_tisserand_invariant, earth_minimum_orbit_intersection_distance,
                    orbit_id, object_designation, close_approach_epoch_unix,
                    relative_velocity_km_per_sec, relative_velocity_km_per_hour,
                    relative_velocity_miles_per_hour, miss_distance_astronomical,
                    miss_distance_lunar, miss_distance_kilometers, orbiting_body,
                    nasa_data_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                # Extract diameter values
                diameter = asteroid.get('estimated_diameter', {})
                diameter_km = diameter.get('kilometers', {})
                
                # Extract velocity values
                velocity = close_approach_data.get('relative_velocity', {})
                
                # Extract distance values
                distance = close_approach_data.get('miss_distance', {})
                
                # Extract orbital values
                orbital = orbital_data.get('orbit', {})
                
                values = (
                    asteroid.get('id'),
                    asteroid.get('name'),
                    asteroid.get('nasa_jpl_url'),
                    asteroid.get('absolute_magnitude_h'),
                    diameter_km.get('estimated_diameter_min'),
                    diameter_km.get('estimated_diameter_max'),
                    asteroid.get('is_potentially_hazardous_asteroid'),
                    asteroid.get('is_sentry_object'),
                    close_approach_data.get('close_approach_date'),
                    close_approach_data.get('close_approach_full'),
                    orbital.get('epoch_osculation'),
                    orbital.get('eccentricity'),
                    orbital.get('semi_major_axis'),
                    orbital.get('inclination'),
                    orbital.get('ascending_node_longitude'),
                    orbital.get('orbital_period'),
                    orbital.get('perihelion_distance'),
                    orbital.get('perihelion_argument'),
                    orbital.get('aphelion_distance'),
                    orbital.get('perihelion_time'),
                    orbital.get('mean_anomaly'),
                    orbital.get('mean_motion'),
                    orbital.get('equinox'),
                    orbital.get('orbit_determination_date'),
                    orbital.get('orbit_uncertainty'),
                    orbital.get('minimum_orbit_intersection'),
                    orbital.get('jupiter_tisserand_invariant'),
                    orbital.get('earth_minimum_orbit_intersection_distance'),
                    orbital.get('orbit_id'),
                    orbital.get('object_designation'),
                    close_approach_data.get('epoch_osculation'),
                    velocity.get('kilometers_per_second'),
                    velocity.get('kilometers_per_hour'),
                    velocity.get('miles_per_hour'),
                    distance.get('astronomical'),
                    distance.get('lunar'),
                    distance.get('kilometers'),
                    close_approach_data.get('orbiting_body'),
                    json.dumps(asteroid, default=str),
                    datetime.now()
                )
                
                cursor.execute(sql, values)
            
            connection.commit()
            logger.info(f"Successfully stored {len(asteroid_data)} records in SQL Database")
            
        except Exception as e:
            connection.rollback()
            logger.error(f"Error storing data in SQL Database: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def store_processed_insights_sql(self, asteroid_data: List[Dict]):
        """Store processed insights in Azure SQL Database.
        
        Args:
            asteroid_data: List of processed asteroid data dictionaries
        """
        connection = self._get_sql_connection()
        cursor = connection.cursor()
        
        try:
            for asteroid in asteroid_data:
                # Calculate insights
                insights = self._calculate_insights(asteroid)
                
                # Prepare SQL insert statement
                sql = """
                INSERT INTO processed_asteroid_insights (
                    raw_asteroid_id, name, risk_score, hazard_level, size_category,
                    orbit_type, inclination_type, velocity_category, distance_category,
                    days_to_approach, is_high_priority, threat_level, recommended_action,
                    orbital_insights, size_insights, velocity_insights, distance_insights,
                    processing_metadata, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                values = (
                    asteroid.get('id'),
                    asteroid.get('name'),
                    asteroid.get('risk_score', 0.0),
                    asteroid.get('hazard_level', 'LOW'),
                    insights.get('size_category'),
                    insights.get('orbit_type'),
                    insights.get('inclination_type'),
                    insights.get('velocity_category'),
                    insights.get('distance_category'),
                    insights.get('days_to_approach'),
                    insights.get('is_high_priority', False),
                    insights.get('threat_level'),
                    insights.get('recommended_action'),
                    json.dumps(insights.get('orbital_insights', {})),
                    json.dumps(insights.get('size_insights', {})),
                    json.dumps(insights.get('velocity_insights', {})),
                    json.dumps(insights.get('distance_insights', {})),
                    json.dumps(insights.get('processing_metadata', {})),
                    datetime.now()
                )
                
                cursor.execute(sql, values)
            
            connection.commit()
            logger.info(f"Successfully stored {len(asteroid_data)} processed insights in SQL Database")
            
        except Exception as e:
            connection.rollback()
            logger.error(f"Error storing processed insights in SQL Database: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def _calculate_insights(self, asteroid: Dict) -> Dict:
        """Calculate comprehensive insights for an asteroid.
        
        Args:
            asteroid: Asteroid data dictionary
            
        Returns:
            Dictionary of calculated insights
        """
        insights = {}
        
        # Size category
        diameter = asteroid.get('estimated_diameter', {}).get('kilometers', {}).get('estimated_diameter_max', 0)
        if diameter < 0.1:
            insights['size_category'] = 'Small (< 100m)'
        elif diameter < 1:
            insights['size_category'] = 'Medium (100m - 1km)'
        else:
            insights['size_category'] = 'Large (> 1km)'
        
        # Orbit type
        orbital_data = asteroid.get('orbital_data', {})
        if 'eccentricity' in orbital_data:
            ecc = float(orbital_data['eccentricity'])
            if ecc < 0.1:
                insights['orbit_type'] = 'Nearly Circular'
            elif ecc < 0.3:
                insights['orbit_type'] = 'Low Eccentricity'
            else:
                insights['orbit_type'] = 'High Eccentricity'
        
        # Inclination type
        if 'inclination' in orbital_data:
            incl = float(orbital_data['inclination'])
            if incl < 5:
                insights['inclination_type'] = 'Low Inclination'
            elif incl < 20:
                insights['inclination_type'] = 'Medium Inclination'
            else:
                insights['inclination_type'] = 'High Inclination'
        
        # Velocity category
        if 'close_approach_data' in asteroid and asteroid['close_approach_data']:
            velocity = asteroid['close_approach_data'][0].get('relative_velocity', {}).get('kilometers_per_hour', 0)
            if velocity < 20000:
                insights['velocity_category'] = 'Slow'
            elif velocity < 50000:
                insights['velocity_category'] = 'Medium'
            else:
                insights['velocity_category'] = 'Fast'
        
        # Distance category
        if 'close_approach_data' in asteroid and asteroid['close_approach_data']:
            distance = asteroid['close_approach_data'][0].get('miss_distance', {}).get('kilometers', 0)
            if distance < 1000000:
                insights['distance_category'] = 'Very Close'
            elif distance < 5000000:
                insights['distance_category'] = 'Close'
            elif distance < 20000000:
                insights['distance_category'] = 'Moderate'
            else:
                insights['distance_category'] = 'Far'
        
        # Days to approach
        if 'close_approach_data' in asteroid and asteroid['close_approach_data']:
            approach_date_str = asteroid['close_approach_data'][0].get('close_approach_date')
            if approach_date_str:
                try:
                    approach_date = datetime.strptime(approach_date_str, '%Y-%m-%d')
                    days_to_approach = (approach_date - datetime.now()).days
                    insights['days_to_approach'] = days_to_approach
                except ValueError:
                    insights['days_to_approach'] = None
        
        # High priority flag
        risk_score = asteroid.get('risk_score', 0.0)
        insights['is_high_priority'] = risk_score > 0.5
        
        # Threat level
        if risk_score > 0.8:
            insights['threat_level'] = 'CRITICAL'
        elif risk_score > 0.6:
            insights['threat_level'] = 'HIGH'
        elif risk_score > 0.4:
            insights['threat_level'] = 'MEDIUM'
        else:
            insights['threat_level'] = 'LOW'
        
        # Recommended action
        if insights.get('threat_level') == 'CRITICAL':
            insights['recommended_action'] = 'Immediate monitoring and analysis required'
        elif insights.get('threat_level') == 'HIGH':
            insights['recommended_action'] = 'Enhanced monitoring recommended'
        elif insights.get('threat_level') == 'MEDIUM':
            insights['recommended_action'] = 'Standard monitoring sufficient'
        else:
            insights['recommended_action'] = 'Routine observation'
        
        # Processing metadata
        insights['processing_metadata'] = {
            'processed_at': datetime.now().isoformat(),
            'processor_version': '1.0.0',
            'data_source': 'NASA NEO API'
        }
        
        return insights
    
    def process_data(self, mode: str = 'auto'):
        """Main method to process asteroid data based on mode.
        
        Args:
            mode: Processing mode ('auto', 'manual-full', 'manual-incremental', 'manual-validation')
        """
        logger.info(f"Starting asteroid data processing in {mode} mode")
        
        try:
            # Determine data fetch parameters based on mode
            if mode == 'manual-full':
                days = 30  # Full month of data
            elif mode == 'manual-incremental':
                days = 1   # Just today's data
            else:
                days = 7   # Default week of data
            
            # Fetch asteroid data
            asteroid_data = self.fetch_asteroid_data(days)
            
            if not asteroid_data:
                logger.warning("No asteroid data retrieved")
                return
            
            # Store raw data in Blob Storage (NASA API response)
            self.store_raw_data_blob(asteroid_data)
            
            # Store raw data in SQL Database (structured fields)
            self.store_raw_data_sql(asteroid_data)
            
            # Store processed insights in SQL Database (calculated data)
            self.store_processed_insights_sql(asteroid_data)
            
            # Call Azure Function for additional processing if available
            if self.function_url:
                self._call_azure_function(asteroid_data)
            
            logger.info(f"Successfully processed {len(asteroid_data)} asteroid records")
            
        except Exception as e:
            logger.error(f"Error in data processing: {e}")
            raise
    
    def _call_azure_function(self, asteroid_data: List[Dict]):
        """Call Azure Function for additional processing.
        
        Args:
            asteroid_data: Asteroid data to send to function
        """
        try:
            response = requests.post(
                f"{self.function_url}/process-asteroids",
                json={'asteroids': asteroid_data[:10]},  # Send first 10 for processing
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            logger.info("Successfully called Azure Function for additional processing")
        except Exception as e:
            logger.warning(f"Azure Function call failed: {e}")


def main():
    """Main entry point for the asteroid processor."""
    parser = argparse.ArgumentParser(description='Process asteroid data from NASA API')
    parser.add_argument('--mode', default='auto', 
                       choices=['auto', 'manual-full', 'manual-incremental', 'manual-validation'],
                       help='Processing mode')
    parser.add_argument('--storage-connection-string', 
                       default=os.getenv('AZURE_STORAGE_CONNECTION_STRING'),
                       help='Azure Storage connection string')
    parser.add_argument('--sql-connection-string',
                       default=os.getenv('AZURE_SQL_CONNECTION_STRING'),
                       help='Azure SQL Database connection string')
    parser.add_argument('--function-url',
                       default=os.getenv('AZURE_FUNCTION_URL'),
                       help='Azure Function URL')
    
    args = parser.parse_args()
    
    if not args.storage_connection_string:
        logger.error("Azure Storage connection string is required")
        sys.exit(1)
    
    if not args.sql_connection_string:
        logger.error("Azure SQL Database connection string is required")
        sys.exit(1)
    
    # Set up logging
    setup_logging()
    
    # Initialize and run processor
    processor = AsteroidProcessor(
        storage_connection_string=args.storage_connection_string,
        sql_connection_string=args.sql_connection_string,
        function_url=args.function_url
    )
    
    processor.process_data(mode=args.mode)


if __name__ == "__main__":
    main() 