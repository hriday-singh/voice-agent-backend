import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Get database credentials from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "voice_agent_portal")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Create data directory for logs if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Print database connection info
logger.info(f"Using PostgreSQL database: {DB_HOST}:{DB_PORT}/{DB_NAME}")

# Create SQLModel engine
engine = create_engine(DATABASE_URL, echo=False)

@contextmanager
def get_db():
    """
    Provides a database session context manager.
    """
    with Session(engine) as session:
        try:
            yield session
            # Commit any changes when exiting the context without errors
        except Exception as e:
            # Rollback on error
            session.rollback()
            raise

def create_db_and_tables():
    """Create database tables if they don't exist"""
    logger.info(f"Creating database tables in PostgreSQL")
    try:
        # Import all models to ensure they're included in metadata
        # This is critical - importing models here ensures they're registered with SQLModel.metadata
        from app.models.models import Admin, OTP, OTPUsage, AgentConfig, GlobalConfig
        
        # Create all tables defined in SQLModel.metadata
        SQLModel.metadata.create_all(engine)
        logger.info("All database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

def ensure_tables():
    """Create database tables if they don't exist (alias for create_db_and_tables)"""
    create_db_and_tables()

def cleanup_connection():
    """Clean up connection - for application shutdown only"""
    logger.info("Database session cleanup complete") 