import os
from dotenv import load_dotenv
import libsql_experimental as libsql
from contextlib import contextmanager
import threading
import stat
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Get database credentials from environment variables
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Set sync interval to 5 minutes (300 seconds)
SYNC_INTERVAL = 300

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Set broad permissions for the data directory to ensure write access
try:
    # Set permissions to readable/writable/executable by everyone
    # os.chmod(DATA_DIR, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    logger.info(f"Set permissions for data directory: {DATA_DIR}")
except Exception as e:
    logger.warning(f"Warning: Could not set permissions for data directory: {e}")

# For local development or CI/CD environments, can use a local file
LOCAL_DB_FILE = os.path.join(DATA_DIR, "app.db")
logger.info(f"Database file path: {LOCAL_DB_FILE}")

# Print database connection info
if TURSO_DATABASE_URL:
    logger.info(f"Using Turso database: {TURSO_DATABASE_URL}")
else:
    logger.info(f"Using local database file: {LOCAL_DB_FILE}")

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
                try:
                    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
                        # Use Turso with local sync and automatic sync every 5 minutes
                        logger.info(f"Connecting to Turso database with local sync (auto-sync every {SYNC_INTERVAL} seconds)")
                        _connection = libsql.connect(
                            LOCAL_DB_FILE, 
                            sync_url=TURSO_DATABASE_URL,
                            auth_token=TURSO_AUTH_TOKEN,
                            sync_interval=SYNC_INTERVAL  # Auto-sync every 5 minutes
                        )
                        logger.info(f"Turso connection created: {_connection}")
                        try:
                            # Initial sync with remote database
                            _connection.sync()
                            logger.info("Initial sync with Turso database successful")
                        except Exception as e:
                            logger.warning(f"Warning: Could not sync with Turso database: {e}")
                    else:
                        # Local only for development
                        logger.info("Connecting to local database file only")
                        _connection = libsql.connect(LOCAL_DB_FILE)
                        logger.info("Local database initialized successfully")
                except Exception as e:
                    logger.error(f"Error connecting to database: {e}")
                    raise
    
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
    # Don't close the connection as it's shared

def ensure_tables():
    """Create database tables if they don't exist"""
    logger.info(f"Creating database tables in: {LOCAL_DB_FILE}")
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
        logger.info("Created admins table")
        
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
        logger.info("Created otps table")
        
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
        logger.info("Created otp_usages table")
        
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
        logger.info("Created agent_traffic table")

        # Synchronize changes to remote database if using Turso
        if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
            conn.sync()
            logger.info("Synced table creation with remote database")
        
        # Commit changes
        conn.commit()
        logger.info("All database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        conn.rollback()
        raise

def sync_with_remote():
    """Sync local database with Turso remote database"""
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        conn = get_connection()
        try:
            logger.info("Starting sync with remote Turso database...")
            conn.sync()
            logger.info("Database synchronized with Turso remote server successfully")
            
            # Verify tables exist after sync
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [table[0] for table in tables]
            logger.info(f"Tables after sync: {table_names}")
            
            return True
        except Exception as e:
            logger.error(f"Error synchronizing with remote database: {e}")
            return False

def cleanup_connection():
    """Clean up the global connection - for application shutdown only"""
    global _connection
    
    if _connection is not None:
        with _connection_lock:
            # Perform a final sync if using Turso
            if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
                try:
                    _connection.sync()
                    logger.info("Final sync completed before shutdown")
                except Exception as e:
                    logger.error(f"Error during final sync: {e}")
            
            _connection = None
            logger.info("Database connection cleaned up") 