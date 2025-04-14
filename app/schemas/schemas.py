# DEPRECATED: This file is deprecated. Please use the modular schema files instead:
# - admin.py: Admin schemas
# - otp.py: OTP and OTP usage schemas
# - agent.py: Agent configuration and traffic schemas
# - common.py: Common utility schemas like Token, Response, etc.
# - responses.py: Pagination and list response schemas

# For backward compatibility, all schemas are re-exported in __init__.py
# So you can still import from app.schemas

# This file will be removed in a future version
import warnings

warnings.warn(
    "Importing directly from schemas.py is deprecated. "
    "Please import from app.schemas instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all schemas for backward compatibility
from app.schemas import *

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from pydantic import EmailStr

# OTP Schemas
class OTPBase(BaseModel):
    code: str
    max_uses: int = 5
    remaining_uses: Optional[int] = None
    description: Optional[str] = None

class OTPCreate(OTPBase):
    count: int = Field(1, ge=1, description="Number of OTPs to generate")
    max_uses: int = Field(5, ge=1, description="Maximum uses for each OTP")

class OTPUpdate(BaseModel):
    max_uses: int = Field(ge=1, description="Maximum number of uses for the OTP")

class OTPResponse(OTPBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Admin Schemas
class AdminBase(BaseModel):
    username: str

class AdminLogin(AdminBase):
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class AdminResponse(AdminBase):
    id: int
    is_active: bool
    
    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    user_type: str  # "admin" or "otp"
    otp_code: Optional[str] = None

# OTP Login Schema
class OTPLogin(BaseModel):
    otp_code: str

class OTPLoginRequest(BaseModel):
    otp_code: str

# Agent Usage Schema
class AgentUsage(BaseModel):
    agent_type: str

# Disconnect Request Schema
class DisconnectRequest(BaseModel):
    agent_type: str
    conversation_id: Optional[str] = None  # Optional because we can use the token subject if not provided

# OTP Usage Schema
class OTPUsageResponse(BaseModel):
    id: int
    otp_id: int
    agent_type: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

# Conversation schemas
class ConversationBase(BaseModel):
    agent_type: str

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: str
    created_at: datetime
    
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

# Response Models for Lists
class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class UsageListResponse(BaseModel):
    data: List[OTPUsageResponse]
    pagination: PaginatedResponse