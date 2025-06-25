#!/usr/bin/env python3
"""
Database Schema Deployment Script
Deploys the asteroid insights database schema using pyodbc
"""

import pyodbc
import os
import sys
from pathlib import Path

def get_connection_string():
    """Get SQL connection string from environment or construct it"""
    # Try to get from environment first
    conn_str = os.getenv('AZURE_SQL_CONNECTION_STRING')
    if conn_str:
        return conn_str
    
    # Construct from components
    server = "asteroiddb0624210145.database.windows.net"
    database = "asteroid_insights"
    username = "asteroidadmin"
    
    # Read password from file
    password_file = Path('.sql_password')
    if password_file.exists():
        with open(password_file, 'r') as f:
            password = f.read().strip()
    else:
        print("Error: .sql_password file not found")
        sys.exit(1)
    
    return f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={database};Uid={username};Pwd={password};"

def deploy_schema():
    """Deploy the database schema"""
    try:
        # Read the schema file
        schema_file = Path('sql/schema.sql')
        if not schema_file.exists():
            print(f"Error: Schema file not found at {schema_file}")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Connect to database
        print("Connecting to Azure SQL Database...")
        conn_str = get_connection_string()
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Connected successfully!")
        
        # Split the schema into individual statements
        # Remove GO statements and split by semicolons
        statements = []
        current_statement = ""
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            if line.upper() == 'GO':
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
            elif line and not line.startswith('--'):
                current_statement += line + " "
        
        # Add the last statement if it exists
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        # Execute each statement
        print(f"Executing {len(statements)} SQL statements...")
        
        for i, statement in enumerate(statements, 1):
            if statement.strip():
                try:
                    print(f"Executing statement {i}/{len(statements)}...")
                    cursor.execute(statement)
                    conn.commit()
                    print(f"✓ Statement {i} executed successfully")
                except Exception as e:
                    print(f"✗ Error in statement {i}: {e}")
                    print(f"Statement: {statement[:100]}...")
                    return False
        
        print("Schema deployment completed successfully!")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sys.tables WHERE name IN ('raw_asteroid_data', 'processed_asteroid_insights')")
        tables = [row[0] for row in cursor.fetchall()]
        
        if len(tables) == 2:
            print(f"✓ Tables created: {', '.join(tables)}")
        else:
            print(f"⚠ Warning: Expected 2 tables, found {len(tables)}: {tables}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error deploying schema: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Deploying Asteroid Insights Database Schema")
    print("=" * 50)
    
    success = deploy_schema()
    
    if success:
        print("\n✅ Schema deployment completed successfully!")
        print("Next steps:")
        print("1. Update your .env file with the new SQL connection string")
        print("2. Test the ETL processor")
        print("3. Set up Azure DevOps pipeline")
    else:
        print("\n❌ Schema deployment failed!")
        sys.exit(1) 