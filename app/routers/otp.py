from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.models import OTP
from app.schemas.schemas import OTPResponse, OTPCreate, OTPUpdate, TokenData, OTPLoginRequest, Token
from app.utils.auth import get_token_data, generate_otp, create_access_token
from app.database.db import get_db
from datetime import datetime, timedelta

router = APIRouter(prefix="/otps", tags=["OTP Management"])

@router.get("/", response_model=List[OTPResponse])
async def get_all_otps(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Get all OTPs (admin only)
    """
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    otps = db.query(OTP).order_by(OTP.created_at.desc()).all()
    return otps

@router.post("/", response_model=List[OTPResponse])
async def create_otps(
    otp_data: OTPCreate,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Generate new OTPs with specified maximum uses (admin only)
    """
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    new_otps = []
    for _ in range(otp_data.count):
        otp_code = generate_otp()
        db_otp = OTP(
            code=otp_code,
            max_uses=otp_data.max_uses,
            remaining_uses=otp_data.max_uses,
            is_used=False
        )
        db.add(db_otp)
        new_otps.append(db_otp)
    
    db.commit()
    
    # Refresh OTP objects to get their IDs
    for otp in new_otps:
        db.refresh(otp)
    
    return new_otps

@router.put("/{otp_id}", response_model=OTPResponse)
async def update_otp(
    otp_id: int,
    otp_data: OTPUpdate,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Update an OTP's maximum number of uses (admin only)
    
    - Sets both max_uses and remaining_uses to the new value
    - Resets is_used flag to false
    - Resets tries counter to 0
    """
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    db_otp = db.query(OTP).filter(OTP.id == otp_id).first()
    if not db_otp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OTP not found"
        )
    
    # Update both max_uses and remaining_uses
    db_otp.max_uses = otp_data.max_uses
    db_otp.remaining_uses = otp_data.max_uses
    # Reset usage flags
    db_otp.is_used = False
    db_otp.tries = 0
    
    db.commit()
    db.refresh(db_otp)
    
    return db_otp

@router.delete("/{otp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_otp(
    otp_id: int,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Delete an OTP (admin only)
    """
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    db_otp = db.query(OTP).filter(OTP.id == otp_id).first()
    if not db_otp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OTP not found"
        )
    
    db.delete(db_otp)
    db.commit()
    
    return 

@router.post("/login", response_model=Token)
async def login_with_otp(
    data: OTPLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with OTP code
    
    - Requires a valid OTP code
    - Checks if OTP is not expired and has remaining uses
    - Returns a JWT token upon successful login
    """
    # Find the OTP by code
    otp = db.query(OTP).filter(OTP.code == data.otp_code).first()
    
    if not otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP code"
        )
    
    # Check if OTP has expired
    if otp.expires_at and otp.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP has expired"
        )
    
    # Check if OTP is exhausted
    if otp.is_used or otp.remaining_uses <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP has been exhausted"
        )
    
    # Generate access token for OTP user
    access_token_expires = timedelta(minutes=60)  # 1 hour token validity
    access_token = create_access_token(
        data={
            "username": f"otp_user_{otp.id}",
            "user_type": "otp", 
            "otp_code": otp.code
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,  # 1 hour in seconds
        "remaining_uses": otp.remaining_uses
    } 