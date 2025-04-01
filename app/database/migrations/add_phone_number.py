import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from app.database.db import DATABASE_URL

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.insert(0, project_root)

def migrate():
    """Add missing columns to otps table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Add all missing columns if they don't exist
        try:
            conn.execute(text("""
                ALTER TABLE otps 
                ADD COLUMN max_uses INTEGER DEFAULT 5;
            """))
        except Exception:
            pass  # Column might already exist
            
        try:
            conn.execute(text("""
                ALTER TABLE otps 
                ADD COLUMN remaining_uses INTEGER DEFAULT 5;
            """))
        except Exception:
            pass  # Column might already exist
            
        try:
            conn.execute(text("""
                ALTER TABLE otps 
                ADD COLUMN expires_at TIMESTAMP;
            """))
        except Exception:
            pass  # Column might already exist
            
        conn.commit()

if __name__ == "__main__":
    migrate() 