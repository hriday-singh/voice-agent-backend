from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.db import get_db, ensure_tables, DB_NAME, DB_HOST, cleanup_connection
from app.routers import auth, otp, agents, admin_agents, admin_llm
from app.utils.dynamic_agents import set_app, initialize_agents
from app.utils.auth import get_password_hash
from app.models.models import Admin
from sqlmodel import Session, select
import os
from dotenv import load_dotenv
import secrets
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create a more secure database if SECRET_KEY isn't set
if not os.getenv("SECRET_KEY"):
    logger.warning("WARNING: No SECRET_KEY found in environment. Generating a random key for this session.")
    os.environ["SECRET_KEY"] = secrets.token_hex(32)

# Debug database connection
logger.info(f"Using PostgreSQL database: {DB_HOST}/{DB_NAME}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database FIRST
    logger.info("Initializing database...")
    try:
        # Create tables before anything else
        logger.info("Creating database tables...")
        ensure_tables()
        logger.info("Database tables created successfully")
        
        # Create default admin on startup
        with get_db() as session:
            try:
                # First try to query the admin
                logger.info("Checking if admin exists...")
                admin = session.exec(select(Admin).where(Admin.username == "cawadmin")).first()
                
                if not admin:
                    # Create default admin
                    logger.info("Admin not found, creating default admin account...")
                    admin = Admin(
                        username="cawadmin",
                        password_hash=get_password_hash("adminc@w")
                    )
                    session.add(admin)
                    session.commit()
                    logger.info("Created default admin account: username='cawadmin', password='adminc@w'")
                else:
                    logger.info("Admin account already exists")
                      
            except Exception as e:
                logger.error(f"Error during startup configuration: {e}")
                raise
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise
    
    # Initialize and mount all enabled agents
    logger.info("Initializing voice agents...")
    set_app(app)  # Set the FastAPI app instance first
    initialize_agents()  # Then initialize all agents
    logger.info("Voice agents initialized successfully")
    
    yield
    
    # Clean up database connection on shutdown
    logger.info("Cleaning up database connection...")
    cleanup_connection()

# Initialize the FastAPI app
app = FastAPI(
    title="Voice Agent Portal API",
    description="API for voice agent portal with OTP-based authentication",
    version="1.0.0",
    lifespan=lifespan,
    redoc_url=None,  # Disable ReDoc in production
    docs_url="/api/docs" if os.getenv("ENVIRONMENT") == "development" else None,  # Only enable Swagger in development
)

# Define allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost",
    os.getenv("FRONTEND_URL", "")
]

# Filter out empty strings from ALLOWED_ORIGINS
ALLOWED_ORIGINS = [origin for origin in ALLOWED_ORIGINS if origin]

# Add CORS middleware with settings for credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Must specify exact origins when using credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Authorization",
        "Access-Control-Allow-Credentials",
        "Access-Control-Allow-Origin",
    ],
    max_age=3600,
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Add routers
app.include_router(auth.router, prefix="/api")
app.include_router(otp.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(admin_agents.router, prefix="/api")
app.include_router(admin_llm.router, prefix="/api")

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring systems"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }
