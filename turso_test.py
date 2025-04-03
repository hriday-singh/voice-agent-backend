#!/usr/bin/env python3
"""
Test script for Turso database connection
Following the official documentation: https://docs.turso.tech/sdk/python/quickstart
"""

import os
import libsql_experimental as libsql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database credentials
url = os.getenv("TURSO_DATABASE_URL")
auth_token = os.getenv("TURSO_AUTH_TOKEN")

print(f"TURSO_DATABASE_URL: {url}")
print(f"TURSO_AUTH_TOKEN: {auth_token}")

if not url or not auth_token:
    print("Error: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set in .env file")
    exit(1)

print(f"Connecting to Turso database: {url}")

try:
    # Connect to Turso database with embedded replica
    # Note: According to documentation, auth_token is passed directly as a parameter
    conn = libsql.connect(
        "turso_test.db",  # Local database file
        sync_url=url,
        auth_token=auth_token
    )
    
    # Sync with remote database
    print("Syncing with remote database...")
    conn.sync()
    
    # Create a test table
    print("Creating test table...")
    conn.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)")
    
    # Insert some data
    print("Inserting test data...")
    conn.execute("INSERT INTO test_table (name) VALUES (?)", ("Test user",))
    
    # Commit changes locally
    conn.commit()
    
    # Sync changes to remote
    print("Syncing changes to remote...")
    conn.sync()
    
    # Query the data
    print("Querying data...")
    result = conn.execute("SELECT * FROM test_table").fetchall()
    print(f"Result: {result}")
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
    exit(1) 