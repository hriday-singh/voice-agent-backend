from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.models import get_all_otps, create_otp, update_otp_usage, get_otp_by_code
from app.schemas.schemas import OTPResponse, OTPCreate, OTPUpdate, TokenData, OTPLoginRequest, Token
from app.utils.auth import get_token_data, generate_otp, create_access_token
from app.database.db import get_db
from datetime import datetime, timedelta
from app.models.models import OTP

router = APIRouter(prefix="/otps", tags=["OTP Management"])

@router.get("/", response_model=List[OTPResponse])
async def get_all_otps_endpoint(
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
    
    with get_db() as conn:
        otps, _ = get_all_otps(conn)
        # The OTP objects are already OTPResponse objects, no need to convert
        return otps

@router.post("/", response_model=List[OTPResponse])
async def create_otps_endpoint(
    otp_data: OTPCreate,
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
    
    with get_db() as conn:
        for _ in range(otp_data.count):
            otp_code = generate_otp()
            # Calculate expiry time - optional
            expires_at = datetime.now() + timedelta(days=30)  # 30 days validity
            
            # Create OTP in database
            otp_id = create_otp(
                conn, 
                code=otp_code, 
                max_uses=otp_data.max_uses,
                expires_at=expires_at
            )
            
            # Get the created OTP
            otp = get_otp_by_code(conn, otp_code)
            
            # Add to response list
            new_otps.append(otp)
    
    return new_otps

@router.put("/{otp_id}", response_model=OTPResponse)
async def update_otp_endpoint(
    otp_id: int,
    otp_data: OTPUpdate,
    token_data: TokenData = Depends(get_token_data)
):
    """
    Update an OTP's maximum number of uses (admin only)
    
    - Sets both max_uses and remaining_uses to the new value
    - Resets is_used flag to false
    """
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    with get_db() as session:
        # Check if OTP exists
        otp = session.get(OTP, otp_id)
        
        if not otp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OTP not found"
            )
        
        # Update OTP
        otp.max_uses = otp_data.max_uses
        otp.remaining_uses = otp_data.max_uses
        otp.is_used = False
        
        session.add(otp)
        session.commit()
        session.refresh(otp)
        
        # Return OTPResponse
        return OTPResponse(
            id=otp.id,
            code=otp.code,
            max_uses=otp.max_uses,
            remaining_uses=otp.remaining_uses,
            is_used=otp.is_used,
            created_at=otp.created_at,
            expires_at=otp.expires_at,
            conversation_id=otp.conversation_id
        )

@router.delete("/{otp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_otp_endpoint(
    otp_id: int,
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
    
    with get_db() as session:
        # Check if OTP exists
        otp = session.get(OTP, otp_id)
        
        if not otp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OTP not found"
            )
        
        # Delete OTP
        session.delete(otp)
        session.commit()
    
    return

@router.post("/login", response_model=Token)
async def login_with_otp(
    data: OTPLoginRequest
):
    """
    Login with OTP code
    
    - Requires a valid OTP code
    - Checks if OTP is not expired and has remaining uses
    - Returns a JWT token upon successful login
    """
    with get_db() as conn:
        # Find the OTP by code
        otp = get_otp_by_code(conn, data.otp_code)
        
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