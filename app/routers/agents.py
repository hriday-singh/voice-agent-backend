from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from app.models.models import get_otp_by_code, update_otp_usage, record_otp_usage
from app.schemas.schemas import TokenData, AgentUsage, DisconnectRequest
from app.utils.auth import get_token_data
from app.database.db import get_db
from datetime import datetime
from app.utils.agent_config import list_available_agents, get_agent_config, get_agent_by_agent_type
import json

router = APIRouter(prefix="/agents", tags=["Agents"])

# Constants
DEFAULT_LIST_LIMIT = 10

@router.get("/list")
async def get_available_agents(
    limit: Optional[int] = Query(DEFAULT_LIST_LIMIT, ge=1, le=50, description="Maximum number of agents to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of agents to skip"),
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
        with get_db() as session:
            otp = get_otp_by_code(session, token_data.otp_code)
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
    if token_data.user_type == "admin":
        agents = list_available_agents(include_disabled=True)
    else:
        agents = list_available_agents(include_disabled=False)
    
    # Add api endpoints to each agent
    for agent in agents:
        agent_type = agent.get("id")
        if agent_type:
            agent["auth_required"] = True
            agent["auth_type"] = "Bearer Token (JWT)"
            agent["connection_type"] = "WebRTC"
    
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
    token_data: TokenData = Depends(get_token_data)
):
    """
    Access an agent without decrementing OTP uses

    Args:
        agent_data: AgentUsage object containing the agent type
        token_data: TokenData object containing the user type and OTP code

    Returns:
        Dict containing:
        - message: Success message
        - remaining_uses: Remaining OTP uses (only for OTP users)
        - agent_info: Dict containing:
            - is_outbound: Whether agent supports outbound calls
            - limitations: List of agent limitations
            - primary_language: Primary language code
            - supported_languages: Dict of supported languages
    """
    # Check if the agent type is valid using the configuration
    agent_config = get_agent_by_agent_type(agent_data.agent_type)
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
    
    # For OTP users, check if OTP is still valid but don't decrement
    remaining_uses = None
    if token_data.user_type == "otp":
        with get_db() as session:
            otp = get_otp_by_code(session, token_data.otp_code)
            
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
            
            # Get remaining uses without decrementing
            remaining_uses = otp.remaining_uses
    
    # Get agent languages
    languages = json.loads(agent_config.get("languages", "{}"))
    primary_language = languages.get("primary", "en-IN")
    supported_languages = languages.get("supported", [])
    
    # Get agent limitations
    limitations = json.loads(agent_config.get("limitations", "[]"))
    
    return {
        "message": f"Access granted to {agent_data.agent_type} agent",
        "remaining_uses": remaining_uses if token_data.user_type == "otp" else None,
        "agent_info": {
            "is_outbound": agent_config.get("is_outbound", False),
            "limitations": limitations,
            "primary_language": primary_language,
            "supported_languages": supported_languages
        }
    }

@router.post("/connect", status_code=status.HTTP_200_OK)
async def connect_agent(
    agent_data: AgentUsage,
    token_data: TokenData = Depends(get_token_data)
):
    """
    Connect to an agent and record the usage (decrements OTP uses if applicable)

    Args:
        agent_data: AgentUsage object containing the agent type
        token_data: TokenData object containing the user type and OTP code

    Returns:
        Dict containing the message and remaining uses (only for OTP users)
    """
    # Check if the agent type is valid using the configuration
    agent_config = get_agent_by_agent_type(agent_data.agent_type)
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
        with get_db() as session:
            otp = get_otp_by_code(session, token_data.otp_code)
            
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
            update_otp_usage(session, otp.id)
            
            # Record the usage
            record_otp_usage(session, otp.id, agent_data.agent_type)
            
            # Get updated remaining uses
            updated_otp = get_otp_by_code(session, token_data.otp_code)
            remaining_uses = updated_otp.remaining_uses if updated_otp else 0
    
    return {
        "message": f"Connected to {agent_data.agent_type} agent",
        "remaining_uses": remaining_uses if token_data.user_type == "otp" else None
    }

@router.post("/disconnect", status_code=status.HTTP_200_OK)
async def disconnect_agent(
    request: DisconnectRequest,
    token_data: TokenData = Depends(get_token_data)
):
    """
    Disconnect from an agent and clear the conversation history
    
    Args:
        request: DisconnectRequest object containing the agent type and optional conversation ID
        token_data: TokenData object containing the user type and OTP code
        
    Returns:
        Dict containing the message and status
    """
    # Check if the agent type is valid
    agent_config = get_agent_by_agent_type(request.agent_type)
    if not agent_config:
        valid_agent_types = get_agent_config().get("agents", {}).keys()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent type. Available types: {list(valid_agent_types)}"
        )
    
    # Create conversation ID format
    conversation_id = request.conversation_id if request.conversation_id else token_data.sub
    
    return {
        "message": f"Disconnected from {request.agent_type} agent",
        "conversation_id": conversation_id,
        "success": True,
        "details": "Conversation history cleared"
    } 