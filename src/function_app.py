import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any

from asteroid_processor import AsteroidProcessor

app = func.FunctionApp()

@app.function_name(name="process_asteroids")
@app.route(route="process-asteroids")
def process_asteroids(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function to process asteroid data.
    
    Args:
        req: HTTP request object
        
    Returns:
        HTTP response with processing results
    """
    logging.info('Python HTTP trigger function processed a request.')
    
    try:
        # Get connection strings from environment
        storage_connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        sql_connection_string = os.getenv('AZURE_SQL_CONNECTION_STRING')
        
        if not storage_connection_string or not sql_connection_string:
            return func.HttpResponse(
                "Missing required environment variables",
                status_code=500
            )
        
        # Initialize processor
        processor = AsteroidProcessor(
            storage_connection_string=storage_connection_string,
            sql_connection_string=sql_connection_string
        )
        
        # Get request body
        try:
            req_body = req.get_json()
            mode = req_body.get('mode', 'auto')
            days = req_body.get('days', 7)
        except ValueError:
            mode = 'auto'
            days = 7
        
        # Process data
        processor.process_data(mode=mode)
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": f"Processed asteroid data in {mode} mode",
                "timestamp": datetime.now().isoformat()
            }),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error processing asteroids: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )

@app.function_name(name="health_check")
@app.route(route="health")
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for the function app.
    
    Args:
        req: HTTP request object
        
    Returns:
        HTTP response with health status
    """
    logging.info('Health check endpoint called.')
    
    try:
        # Check environment variables
        storage_connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        sql_connection_string = os.getenv('AZURE_SQL_CONNECTION_STRING')
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "storage_connection": bool(storage_connection_string),
                "sql_connection": bool(sql_connection_string),
                "function_runtime": "python"
            }
        }
        
        # Check if all required variables are present
        if not all(health_status["checks"].values()):
            health_status["status"] = "unhealthy"
            return func.HttpResponse(
                json.dumps(health_status),
                status_code=503,
                mimetype="application/json"
            )
        
        return func.HttpResponse(
            json.dumps(health_status),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }),
            status_code=503,
            mimetype="application/json"
        )

@app.function_name(name="get_asteroid_stats")
@app.route(route="stats")
def get_asteroid_stats(req: func.HttpRequest) -> func.HttpResponse:
    """Get asteroid processing statistics.
    
    Args:
        req: HTTP request object
        
    Returns:
        HTTP response with statistics
    """
    logging.info('Statistics endpoint called.')
    
    try:
        # Get connection strings
        storage_connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        sql_connection_string = os.getenv('AZURE_SQL_CONNECTION_STRING')
        
        if not storage_connection_string or not sql_connection_string:
            return func.HttpResponse(
                "Missing required environment variables",
                status_code=500
            )
        
        # Initialize processor to get database connection
        processor = AsteroidProcessor(
            storage_connection_string=storage_connection_string,
            sql_connection_string=sql_connection_string
        )
        
        # Get statistics from database
        connection = processor._get_sql_connection()
        cursor = connection.cursor()
        
        try:
            # Get total asteroid count
            cursor.execute("SELECT COUNT(*) FROM raw_asteroid_data")
            total_asteroids = cursor.fetchone()[0]
            
            # Get high-risk asteroids count
            cursor.execute("SELECT COUNT(*) FROM processed_asteroid_insights WHERE risk_score > 0.7")
            high_risk_count = cursor.fetchone()[0]
            
            # Get hazardous asteroids count
            cursor.execute("SELECT COUNT(*) FROM raw_asteroid_data WHERE is_potentially_hazardous_asteroid = 1")
            hazardous_count = cursor.fetchone()[0]
            
            # Get latest processing date
            cursor.execute("SELECT MAX(fetched_at) FROM raw_asteroid_data")
            latest_date = cursor.fetchone()[0]
            
            stats = {
                "total_asteroids": total_asteroids,
                "high_risk_asteroids": high_risk_count,
                "hazardous_asteroids": hazardous_count,
                "latest_processing_date": latest_date.isoformat() if latest_date else None,
                "timestamp": datetime.now().isoformat()
            }
            
            return func.HttpResponse(
                json.dumps(stats),
                mimetype="application/json"
            )
            
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e:
        logging.error(f"Error getting statistics: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        ) 