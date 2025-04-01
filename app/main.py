from fastapi import FastAPI, Depends, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database.db import engine, Base, get_db, DATABASE_URL
from app.models.models import Admin
from app.routers import auth, otp, agents, admin_agents
from app.utils.agents import realestate_agent, hospital_agent
from app.utils.auth import get_password_hash, get_token_data
import os
from dotenv import load_dotenv
import secrets
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Create a more secure database if SECRET_KEY isn't set
if not os.getenv("SECRET_KEY"):
    print("WARNING: No SECRET_KEY found in environment. Generating a random key for this session.")
    os.environ["SECRET_KEY"] = secrets.token_hex(32)

# Debug database connection
print(f"Using database URL: {DATABASE_URL}")

# Create tables in the database
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create default admin on startup
    db = next(get_db())
    admin = db.query(Admin).filter(Admin.username == "cawadmin").first()
    if not admin:
        admin = Admin(
            username="cawadmin",
            password_hash=get_password_hash("adminc@w")
        )
        db.add(admin)
        db.commit()
        print("Created default admin account: username='cawadmin', password='adminc@w'")
    yield

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
    os.getenv("FRONTEND_URL", ""),
]

# Filter out empty strings from ALLOWED_ORIGINS
ALLOWED_ORIGINS = [origin for origin in ALLOWED_ORIGINS if origin]

# Add CORS middleware with strict settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
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

