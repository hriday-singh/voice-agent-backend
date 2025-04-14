from pydantic import BaseModel
from typing import List, Dict, Any, Generic, TypeVar
from app.schemas.common import PaginatedResponse
from app.schemas.otp import OTPUsageResponse

T = TypeVar('T')

class ListResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginatedResponse

class UsageListResponse(BaseModel):
    data: List[OTPUsageResponse]
    pagination: PaginatedResponse 