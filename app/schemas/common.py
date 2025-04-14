from pydantic import BaseModel
from typing import List, Generic, TypeVar, Dict, Any
from datetime import datetime

T = TypeVar('T')

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: str = None
    user_type: str  # "admin" or "otp"
    otp_code: str = None

class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class Response(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = None 