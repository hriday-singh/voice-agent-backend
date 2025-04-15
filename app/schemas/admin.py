from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AdminBase(BaseModel):
    username: str

class AdminCreate(AdminBase):
    password: str

class AdminLogin(AdminBase):
    password: str

class AdminResponse(AdminBase):
    id: int
    conversation_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    current_password: str
    new_password: str 