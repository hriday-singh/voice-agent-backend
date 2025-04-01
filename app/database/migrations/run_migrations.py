import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.insert(0, project_root)

from app.database.migrations import add_phone_number

def run_all_migrations():
    """Run all database migrations in order"""
    print("Running migrations...")
    
    # Add migrations here in order
    migrations = [
        ("Add phone_number to otps", add_phone_number.migrate),
    ]
    
    for name, migrate_func in migrations:
        print(f"Running migration: {name}")
        try:
            migrate_func()
            print(f"✓ {name} completed successfully")
        except Exception as e:
            print(f"✗ {name} failed: {str(e)}")
            raise

if __name__ == "__main__":
    run_all_migrations() 