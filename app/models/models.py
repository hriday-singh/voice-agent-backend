from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.db import Base

class OTP(Base):
    """OTP model to store one-time-passwords"""
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    max_uses = Column(Integer, default=5)  # Maximum number of times OTP can be used
    remaining_uses = Column(Integer, default=5)  # Number of remaining uses
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Relationship to OTPUsage
    usages = relationship("OTPUsage", back_populates="otp", cascade="all, delete-orphan")

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

class OTPUsage(Base):
    """Track when and how OTPs are used"""
    __tablename__ = "otp_usages"

    id = Column(Integer, primary_key=True, index=True)
    otp_id = Column(Integer, ForeignKey("otps.id"), nullable=False)
    agent_type = Column(String, nullable=False)  # e.g., "hospital", "realestate"
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to the OTP
    otp = relationship("OTP", back_populates="usages")

class AgentTraffic(Base):
    __tablename__ = "agent_traffic"

    id = Column(Integer, primary_key=True, index=True)
    agent_type = Column(String, nullable=False)  # e.g., "hospital", "realestate"
    session_count = Column(Integer, default=0)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True) 