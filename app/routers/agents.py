from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.models.models import OTP, OTPUsage, AgentTraffic
from app.schemas.schemas import TokenData, AgentUsage
from app.utils.auth import get_token_data
from app.database.db import get_db
from datetime import datetime
from app.utils.agent_config import list_available_agents, get_agent_config, get_agent_by_id

router = APIRouter(prefix="/agents", tags=["Agents"])

# Constants
DEFAULT_LIST_LIMIT = 10

@router.get("/list")
async def get_available_agents(
    limit: Optional[int] = Query(DEFAULT_LIST_LIMIT, ge=1, le=50, description="Maximum number of agents to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of agents to skip"),
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data)
):
    """
    List available voice agents with their endpoints
    
    Args:
        limit: Maximum number of agents to return (1-50, default 10)
        offset: Number of agents to skip (pagination)
    
    Returns:
        List of agents with their configurations and WebSocket endpoints
    """
    # For OTP users, check if OTP is still valid
    if token_data.user_type == "otp":
        otp = db.query(OTP).filter(OTP.code == token_data.otp_code).first()
        if not otp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP"
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
    
    agents = list_available_agents(include_disabled=False)
    
    # Add WebSocket endpoints to each agent
    for agent in agents:
        agent_type = agent.get("id")
        if agent_type:
            agent["websocket_endpoint"] = f"/api/voice-agents/{agent_type}"
            agent["auth_required"] = True
            agent["auth_type"] = "Bearer Token (JWT)"
            agent["connection_type"] = "WebSocket"
    
    # Apply pagination
    total_count = len(agents)
    agents = agents[offset:offset+limit]
    
    return {
        "agents": agents,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
    }

@router.post("/access", status_code=status.HTTP_200_OK)
async def access_agent(
    agent_data: AgentUsage,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Access an agent and record the usage (decrements OTP uses if applicable)
    """
    # Check if the agent type is valid using the configuration
    agent_config = get_agent_by_id(agent_data.agent_type)
    if not agent_config:
        valid_agent_types = get_agent_config().get("agents", {}).keys()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent type. Available types: {list(valid_agent_types)}"
        )
    
    # Check if the agent is enabled
    if agent_config.get("enabled", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent '{agent_data.agent_type}' is currently disabled"
        )
    
    # For OTP users, we need to decrement the remaining uses
    if token_data.user_type == "otp":
        otp = db.query(OTP).filter(OTP.code == token_data.otp_code).first()
        
        if not otp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP",
            )
        
        # Check if OTP has expired
        if otp.expires_at and otp.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OTP has expired",
            )
        
        if otp.is_used or otp.remaining_uses <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OTP has been exhausted",
            )
        
        # Decrement remaining uses
        otp.remaining_uses -= 1
        if otp.remaining_uses <= 0:
            otp.is_used = True
            
        # Record the usage
        usage = OTPUsage(
            otp_id=otp.id,
            agent_type=agent_data.agent_type,
        )
        db.add(usage)
        
        # Update agent traffic
        agent_traffic = db.query(AgentTraffic).filter(
            AgentTraffic.agent_type == agent_data.agent_type
        ).first()
        
        if not agent_traffic:
            agent_traffic = AgentTraffic(
                agent_type=agent_data.agent_type,
                session_count=1,
                last_activity=datetime.utcnow(),
                is_active=True
            )
            db.add(agent_traffic)
        else:
            agent_traffic.session_count += 1
            agent_traffic.last_activity = datetime.utcnow()
            agent_traffic.is_active = True
        
        db.commit()
    
    return {
        "message": f"Access granted to {agent_data.agent_type} agent",
        "remaining_uses": otp.remaining_uses if token_data.user_type == "otp" else None
    } 