from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class OTPBase(BaseModel):
    code: str
    max_uses: int = 5
    remaining_uses: Optional[int] = None
    is_used: Optional[bool] = None
    expires_at: Optional[datetime] = None

class OTPCreate(OTPBase):
    count: int = Field(1, ge=1, description="Number of OTPs to generate")
    max_uses: int = Field(5, ge=1, description="Maximum uses for each OTP")

class OTPUpdate(BaseModel):
    max_uses: int = Field(ge=1, description="Maximum number of uses for the OTP")

class OTPResponse(OTPBase):
    id: int
    created_at: datetime
    conversation_id: str
    
    class Config:
        from_attributes = True

class OTPLogin(BaseModel):
    otp_code: str

class OTPLoginRequest(BaseModel):
    otp_code: str

class OTPUsageBase(BaseModel):
    otp_id: int
    agent_type: str

class OTPUsageCreate(OTPUsageBase):
    pass

class OTPUsageResponse(OTPUsageBase):
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

class OTPRequestForm(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Full name of the requester")
    email: EmailStr = Field(..., description="Email address")
    phone_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$", description="Phone number (10-15 digits)")
    purpose: str = Field(..., min_length=5, max_length=200, description="Purpose of request")
    company: Optional[str] = Field(None, max_length=100, description="Company name (optional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone_number": "+919876543210",
                "purpose": "I need access to the real estate voice agent for property inquiries",
                "company": "ABC Corporation"
            }
        }

class OTPRequestResponse(BaseModel):
    request_id: str = Field(..., description="Unique ID for the OTP request")
    status: str = Field(..., description="Status of the request (pending/approved/rejected)")
    message: str = Field(..., description="Response message")
    created_at: datetime = Field(..., description="Timestamp of request creation")

class OTPRequestListItem(BaseModel):
    id: int
    name: str
    email: str
    phone_number: str
    purpose: str
    company: Optional[str]
    ip_address: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True 