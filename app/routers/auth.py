from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.database.db import get_db
from app.models.models import get_admin_by_username, update_admin_password, get_otp_by_code
from app.schemas.schemas import Token, AdminLogin, OTPLogin, AdminResponse, PasswordChange, TokenData
from app.utils.auth import verify_password, create_access_token, get_password_hash, get_token_data
from datetime import timedelta, datetime

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login/admin", response_model=Token)
async def login_admin(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate admin user and provide JWT token
    """
    with get_db() as conn:
        admin = get_admin_by_username(conn, form_data.username)
        
        if not admin or not verify_password(form_data.password, admin['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Create access token
        access_token = create_access_token(
            data={"username": admin['username'], "user_type": "admin"}
        )
        
        return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login/otp", response_model=Token)
async def login_otp(otp_data: OTPLogin):
    """
    Authenticate user with OTP and provide JWT token
    """
    with get_db() as conn:
        otp = get_otp_by_code(conn, otp_data.otp_code)
        
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
        
        # Create access token
        access_token = create_access_token(
            data={"user_type": "otp", "otp_code": otp['code']}
        )
        
        return {"access_token": access_token, "token_type": "bearer", "remaining_uses": otp['remaining_uses']}

@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_admin_password(
    password_data: PasswordChange,
    token_data: TokenData = Depends(get_token_data)
):
    """
    Change the admin user's password.
    Requires admin authentication.
    """
    # Check if user is admin
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can change their password"
        )
    
    with get_db() as conn:
        # Get the admin
        admin = get_admin_by_username(conn, token_data.username)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, admin['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password
        if len(password_data.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )
        
        if password_data.new_password == password_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )
        
        # Update the password with explicit transaction
        try:
            # Hash the new password
            new_password_hash = get_password_hash(password_data.new_password)
            # Update admin password
            update_admin_password(conn, admin['id'], new_password_hash)
            
            return {"message": "Password changed successfully"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password. Please try again."
            ) 