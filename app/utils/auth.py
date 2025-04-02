from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import random
import string
import os
from app.schemas.schemas import TokenData
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database.db import get_db
from app.models.models import get_otp_by_code
from decouple import config

# Configure JWT
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 with Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/admin")

# Password utilities
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT token utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_token_data(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        user_type = payload.get("user_type")
        otp_code = payload.get("otp_code")
        
        if user_type not in ["admin", "otp"]:
            raise credentials_exception
            
        # For OTP users, we need both user_type and otp_code
        if user_type == "otp":
            if not otp_code:
                raise credentials_exception
            
            # Use our Turso connection
            with get_db() as conn:
                # Check if OTP exists and is valid
                otp = get_otp_by_code(conn, otp_code)
                if not otp:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid OTP",
                    )
                
                # Check if OTP has expired
                if otp['expires_at'] and otp['expires_at'] < datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="OTP has expired",
                    )
                
                # Check if OTP is exhausted
                if otp['is_used'] or otp['remaining_uses'] <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="OTP has been exhausted",
                    )
            
        # For admin users, we need both user_type and username
        if user_type == "admin" and not username:
            raise credentials_exception
            
        return TokenData(username=username, user_type=user_type, otp_code=otp_code)
    except JWTError:
        raise credentials_exception

async def get_token_from_query(token: str) -> TokenData:
    """
    Verify and decode token from query parameter for WebSocket connections
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        user_type = payload.get("user_type")
        otp_code = payload.get("otp_code")
        
        if user_type not in ["admin", "otp"]:
            raise credentials_exception
            
        # For OTP users, we need both user_type and otp_code
        if user_type == "otp":
            if not otp_code:
                raise credentials_exception
            
            # Use our Turso connection
            with get_db() as conn:
                # Check if OTP exists and is valid
                otp = get_otp_by_code(conn, otp_code)
                if not otp:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid OTP",
                    )
                
                # Check if OTP has expired
                if otp['expires_at'] and otp['expires_at'] < datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="OTP has expired",
                    )
                
                # Check if OTP is exhausted
                if otp['is_used'] or otp['remaining_uses'] <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="OTP has been exhausted",
                    )
            
        # For admin users, we need both user_type and username
        if user_type == "admin" and not username:
            raise credentials_exception
            
        return TokenData(username=username, user_type=user_type, otp_code=otp_code)
    except JWTError:
        raise credentials_exception

# Generate a 6-digit OTP code
def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code"""
    return ''.join(random.choices(string.digits, k=length)) 