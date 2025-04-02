import os
from dotenv import load_dotenv
import libsql_experimental as libsql
from contextlib import contextmanager
import threading

load_dotenv()

# Get database credentials from environment variables
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# For local development or CI/CD environments, can use a local file
LOCAL_DB_FILE = "app.db"

# Print database connection info
if TURSO_DATABASE_URL:
    print(f"Using Turso database: {TURSO_DATABASE_URL}")
else:
    print(f"Using local database file: {LOCAL_DB_FILE}")

# Global shared connection
_connection = None
_connection_lock = threading.Lock()

def get_connection():
    """Get the shared database connection."""
    global _connection
    
    # Create the connection if it doesn't exist
    if _connection is None:
        with _connection_lock:
            # Double-check inside the lock to avoid race conditions
            if _connection is None:
                if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
                    # Use Turso with local sync
                    _connection = libsql.connect(
                        LOCAL_DB_FILE, 
                        sync_url=TURSO_DATABASE_URL,
                        auth_token=TURSO_AUTH_TOKEN
                    )
                    try:
                        # Initial sync with remote database
                        _connection.sync()
                    except Exception as e:
                        print(f"Warning: Could not sync with Turso database: {e}")
                else:
                    # Local only for development
                    _connection = libsql.connect(LOCAL_DB_FILE)
    
    return _connection

@contextmanager
def get_db():
    """
    Provides a database connection context manager.
    Uses a single shared connection for efficiency.
    """
    conn = get_connection()
    try:
        yield conn
        # Commit any changes when exiting the context without errors
        conn.commit()
    except Exception as e:
        # Rollback on error
        conn.rollback()
        raise

def ensure_tables():
    """Create database tables if they don't exist"""
    conn = get_connection()
    
    try:
        # Admin table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        
        # OTP table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                max_uses INTEGER DEFAULT 5,
                remaining_uses INTEGER DEFAULT 5,
                is_used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        # OTP Usage table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS otp_usages (
                id INTEGER PRIMARY KEY,
                otp_id INTEGER NOT NULL,
                agent_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (otp_id) REFERENCES otps (id) ON DELETE CASCADE
            )
        """)
        
        # Agent Traffic table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_traffic (
                id INTEGER PRIMARY KEY,
                agent_type TEXT NOT NULL,
                session_count INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        # Synchronize changes to remote database if using Turso
        if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
            conn.sync()
        
        # Commit changes
        conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")
        conn.rollback()
        raise

def sync_with_remote():
    """Sync local database with Turso remote database"""
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        conn = get_connection()
        try:
            conn.sync()
            print("Database synchronized with Turso remote server")
        except Exception as e:
            print(f"Error synchronizing with remote database: {e}")

def cleanup_connection():
    """Clean up the global connection - for application shutdown only"""
    global _connection
    
    if _connection is not None:
        with _connection_lock:
            _connection = None
            print("Database connection cleaned up") 