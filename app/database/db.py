from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import stat
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

load_dotenv()

# Create a secure data directory
data_dir = Path(os.getenv("DATA_DIR", "data"))
data_dir.mkdir(exist_ok=True)

# Make sure we use an absolute path
data_dir = data_dir.absolute()
logger.info(f"Using data directory: {data_dir}")

# Set restrictive permissions on data directory (owner only)
if os.name != 'nt':  # Skip on Windows
    try:
        os.chmod(data_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    except PermissionError:
        logger.warning(f"Warning: Could not set permissions on {data_dir}, continuing anyway...")

# Check for Turso configuration
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Get database URL from environment variables
if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
    # Use Turso SQLite database
    logger.info("Using Turso SQLite database")
    db_url = f"sqlite+{TURSO_DATABASE_URL}/?authToken={TURSO_AUTH_TOKEN}&secure=true"
    DATABASE_URL = db_url
    
    # Create engine with Turso-specific settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False},
        echo=os.getenv("ENVIRONMENT", "production").lower() == "development"
    )
else:
    # Fallback to local SQLite database
    logger.info("Turso credentials not found, using local SQLite database")
    db_path = data_dir / "app.db"
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_path}")
    
    # Enhanced security for SQLite
    if DATABASE_URL.startswith("sqlite"):
        # SQLite connection args with improved security and thread handling
        connect_args = {
            "check_same_thread": False,  # Allow cross-thread usage
            "timeout": 30  # Wait up to 30 seconds for locks
        }
        
        # Create engine with thread-safe settings
        engine = create_engine(
            DATABASE_URL,
            connect_args=connect_args,
            poolclass=StaticPool,  # Use static pool for better thread handling
            # Disable SQL query logging in production
            echo=os.getenv("ENVIRONMENT", "production").lower() == "development"
        )
        
        # Add security pragmas for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            # Enable secure deletion (slower but more secure)
            cursor.execute("PRAGMA secure_delete=ON")
            # Disable memory mapping to prevent potential exploits
            cursor.execute("PRAGMA mmap_size=0")
            # Use WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            # Set appropriate synchronous mode for WAL
            cursor.execute("PRAGMA synchronous=NORMAL")
            # Temporary files are written to memory
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()
                
        # Set secure permissions on database file after creation
        if os.name != 'nt':  # Skip on Windows
            if db_path.exists():
                try:
                    os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
                except PermissionError:
                    logger.warning(f"Warning: Could not set permissions on {db_path}, continuing anyway...")
    else:
        # For PostgreSQL, MySQL, etc.
        engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={"sslmode": "require"} if not DATABASE_URL.startswith("sqlite") else {},
            echo=os.getenv("ENVIRONMENT", "production").lower() == "development"
        )

# Create session factory with thread-safe settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=True
)

# Base class for models
Base = declarative_base()

# Thread-safe database session dependency
def get_db():
    db = SessionLocal()
    try:
        # Test connection with properly formatted SQL
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    finally:
        db.close() 