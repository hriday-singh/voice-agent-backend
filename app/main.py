from fastapi import FastAPI, Depends, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.database.db import get_db, ensure_tables, TURSO_DATABASE_URL, LOCAL_DB_FILE, sync_with_remote, cleanup_connection
from app.routers import auth, otp, agents, admin_agents
from app.utils.agents import realestate_agent, hospital_agent
from app.utils.auth import get_password_hash, get_token_data
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
if TURSO_DATABASE_URL:
    logger.info(f"Using Turso database")
else:
    logger.info(f"Using local database: {LOCAL_DB_FILE}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    logger.info("Initializing database...")
    try:
        # Sync with remote database at startup if using Turso
        if TURSO_DATABASE_URL:
            logger.info("Syncing with remote Turso database...")
            sync_with_remote()
        
        # Create tables after syncing with remote
        ensure_tables()
        logger.info("Database tables created successfully")
        
        # Create default admin on startup
        with get_db() as conn:
            try:
                # First try to query the admin
                logger.info("Checking if admin exists...")
                admin = conn.execute(
                    "SELECT * FROM admins WHERE username = ?", 
                    ("cawadmin",)
                ).fetchone()
                
                if not admin:
                    # Create default admin
                    logger.info("Admin not found, creating default admin account...")
                    conn.execute(
                        "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                        ("cawadmin", get_password_hash("adminc@w"))
                    )
                    logger.info("Created default admin account: username='cawadmin', password='adminc@w'")
                else:
                    logger.info("Admin account already exists")
                
                # Sync changes back to remote
                if TURSO_DATABASE_URL:
                    logger.info("Syncing changes back to remote Turso database...")
                    conn.sync()
            except Exception as e:
                logger.error(f"Error with admin account setup: {e}")
                raise
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise
    
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
    os.getenv("FRONTEND_URL", ""),
]

# Filter out empty strings from ALLOWED_ORIGINS
ALLOWED_ORIGINS = [origin for origin in ALLOWED_ORIGINS if origin]

# Add CORS middleware with strict settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    #allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_methods=["*"],
    allow_headers=[
        "Authorization", 
        "Content-Type",
        "Access-Control-Allow-Credentials",
        "Access-Control-Allow-Origin",
    ],
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
app.include_router(auth.router, prefix="/api")  # Admin auth endpoints: /api/auth/login/admin
app.include_router(otp.router, prefix="/api")   # OTP endpoints: /api/otps/login
app.include_router(agents.router, prefix="/api")
app.include_router(admin_agents.router, prefix="/api")

# Mount the FastRTC streams at authenticated paths
realestate_agent.stream.mount(app, path="/api/voice-agents/realestate")
hospital_agent.stream.mount(app, path="/api/voice-agents/hospital")

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring systems"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }
