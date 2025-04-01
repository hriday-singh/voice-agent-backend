from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from app.utils.auth import get_token_data
from app.schemas.schemas import (
    TokenData, OTPUsageResponse, AgentTrafficResponse,
    UsageListResponse, TrafficListResponse
)
from app.utils.agent_config import get_agent_config, update_agent_config, get_agent_by_id
from app.utils.prompt_manager import save_prompt_file
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import OTPUsage, AgentTraffic
from datetime import datetime
import re
import os
from pathlib import Path

router = APIRouter(prefix="/admin/agents", tags=["Admin Agent Management"])

# Helper functions
def check_admin_authorization(token_data: TokenData):
    """Check if user is admin"""
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    return True

def validate_agent_id(agent_id: str) -> str:
    """Validate agent ID format (lowercase alphanumeric with underscores)"""
    if not re.match(r'^[a-z0-9_]+$', agent_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent ID must contain only lowercase letters, numbers, and underscores"
        )
    return agent_id

# Usage and Traffic endpoints first
@router.get("/usage", response_model=UsageListResponse)
async def get_agent_usage(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data),
    limit: Optional[int] = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of records to skip")
):
    """
    Get agent usage records (admin only)
    
    Args:
        limit: Maximum number of records to return (1-500)
        offset: Number of records to skip (pagination)
    """
    check_admin_authorization(token_data)
    
    # Get total count for pagination
    total_count = db.query(OTPUsage).count()
    
    # Apply pagination
    usages = db.query(OTPUsage).order_by(OTPUsage.timestamp.desc()).offset(offset).limit(limit).all()
    
    # Clean up old records if we have too many (limit to 500)
    if total_count > 500:
        # Find the oldest records to delete
        oldest_records = db.query(OTPUsage).order_by(OTPUsage.timestamp.asc()).limit(total_count - 500).all()
        for record in oldest_records:
            db.delete(record)
        db.commit()
    
    return UsageListResponse(
        data=usages,
        pagination={
            "total": total_count if total_count <= 500 else 500,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
    )

@router.get("/traffic", response_model=TrafficListResponse)
async def get_agent_traffic(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data),
    limit: Optional[int] = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of records to skip")
):
    """
    Get traffic statistics for agents (admin only)
    
    Args:
        limit: Maximum number of records to return (1-500)
        offset: Number of records to skip (pagination)
    """
    check_admin_authorization(token_data)
    
    # Get total count for pagination
    total_count = db.query(AgentTraffic).count()
    
    # Apply pagination
    traffic = db.query(AgentTraffic).offset(offset).limit(limit).all()
    
    # Clean up old records if we have too many (limit to 500)
    if total_count > 500:
        # Find the oldest records to delete
        oldest_records = db.query(AgentTraffic).order_by(AgentTraffic.last_activity.asc()).limit(total_count - 500).all()
        for record in oldest_records:
            db.delete(record)
        db.commit()
    
    return TrafficListResponse(
        data=traffic,
        pagination={
            "total": total_count if total_count <= 500 else 500,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
    )

@router.delete("/usage/clear")
async def clear_agent_usage(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Clear all agent usage records (admin only)
    
    This operation cannot be undone.
    """
    check_admin_authorization(token_data)
    
    # Count records before deletion
    count = db.query(OTPUsage).count()
    
    # Delete all records
    db.query(OTPUsage).delete()
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully cleared {count} usage records"
    }

@router.delete("/traffic/clear")
async def clear_agent_traffic(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Clear all agent traffic statistics (admin only)
    
    This operation cannot be undone.
    """
    check_admin_authorization(token_data)
    
    # Count records before deletion
    count = db.query(AgentTraffic).count()
    
    # Delete all records
    db.query(AgentTraffic).delete()
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully cleared {count} traffic records"
    }

# CRUD endpoints for agent management
@router.get("/", response_model=Dict[str, Any])
async def get_all_agents(
    token_data: TokenData = Depends(get_token_data)
):
    """
    Get all agent configurations (admin only)
    """
    check_admin_authorization(token_data)
    
    config = get_agent_config()
    return {"agents": config.get("agents", {})}

@router.get("/{agent_id}", response_model=Dict[str, Any])
async def get_agent(
    agent_id: str,
    token_data: TokenData = Depends(get_token_data)
):
    """
    Get a specific agent configuration (admin only)
    """
    check_admin_authorization(token_data)
    
    agent_config = get_agent_by_id(agent_id)
    if not agent_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return agent_config

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: Dict[str, Any] = Body(...),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Create a new agent (admin only)
    
    Required fields:
    - id: Unique agent identifier (lowercase, alphanumeric with underscores)
    - name: Display name for the agent
    - description: Brief description of the agent
    - startup_message: SSML message to play when connection starts
    - prompt: System prompt text for the agent
    """
    check_admin_authorization(token_data)
    
    # Validate required fields
    required_fields = ["id", "name", "description", "startup_message", "prompt"]
    for field in required_fields:
        if field not in agent_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    # Validate and normalize agent ID
    agent_id = validate_agent_id(agent_data["id"])
    
    # Check if agent ID already exists
    config = get_agent_config()
    if agent_id in config.get("agents", {}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent ID '{agent_id}' already exists"
        )
    
    # Save prompt file
    prompt_file_path = save_prompt_file(agent_id, agent_data["prompt"])
    
    # Create new agent config
    new_agent = {
        "name": agent_data["name"],
        "description": agent_data["description"],
        "api_path": f"/api/voice-agents/stream?agent_type={agent_id}",
        "startup_message": agent_data["startup_message"],
        "prompt_file": prompt_file_path,
        "enabled": True
    }
    
    # Update configuration
    agents = config.get("agents", {})
    agents[agent_id] = new_agent
    config["agents"] = agents
    
    # Save updated config
    update_agent_config(config)
    
    return {"message": f"Agent '{agent_id}' created successfully", "agent": new_agent}

@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    agent_data: Dict[str, Any] = Body(...),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Update an existing agent (admin only)
    
    Available fields to update:
    - name: Display name for the agent
    - description: Brief description of the agent
    - startup_message: SSML message to play when connection starts
    - prompt: System prompt text for the agent
    - enabled: Whether the agent is enabled (boolean)
    """
    check_admin_authorization(token_data)
    
    # Check if agent exists
    config = get_agent_config()
    if agent_id not in config.get("agents", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    # Get current agent config
    current_agent = config["agents"][agent_id]
    
    # Update fields
    valid_fields = ["name", "description", "startup_message", "prompt", "enabled"]
    for field in valid_fields:
        if field in agent_data:
            # Special handling for the prompt field
            if field == "prompt" and agent_data["prompt"].strip():
                # Temprarily disabled to not damage exsisting agents
                # prompt_file_path = save_prompt_file(agent_id, agent_data["prompt"])
                # current_agent["prompt_file"] = prompt_file_path
                pass
            elif field != "prompt":
                current_agent[field] = agent_data[field]
    
    # Save updated config
    config["agents"][agent_id] = current_agent
    update_agent_config(config)
    
    return {"message": f"Agent '{agent_id}' updated successfully", "agent": current_agent}

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    token_data: TokenData = Depends(get_token_data)
):
    """
    Delete an agent (admin only)
    """
    check_admin_authorization(token_data)
    
    # Check if agent exists
    config = get_agent_config()
    if agent_id not in config.get("agents", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    # Delete the agent from config
    del config["agents"][agent_id]
    update_agent_config(config)
    
    # Note: We don't delete the prompt file to keep history
    
    return {"message": f"Agent '{agent_id}' deleted successfully"}

@router.put("/{agent_id}/enable")
async def enable_agent(
    agent_id: str,
    token_data: TokenData = Depends(get_token_data)
):
    """
    Enable an agent (admin only)
    """
    check_admin_authorization(token_data)
    
    # Check if agent exists
    config = get_agent_config()
    if agent_id not in config.get("agents", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    # Enable the agent
    config["agents"][agent_id]["enabled"] = True
    update_agent_config(config)
    
    return {"message": f"Agent '{agent_id}' enabled successfully"}

@router.put("/{agent_id}/disable")
async def disable_agent(
    agent_id: str,
    token_data: TokenData = Depends(get_token_data)
):
    """
    Disable an agent (admin only)
    """
    check_admin_authorization(token_data)
    
    # Check if agent exists
    config = get_agent_config()
    if agent_id not in config.get("agents", {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found"
        )
    
    # Disable the agent
    config["agents"][agent_id]["enabled"] = False
    update_agent_config(config)
    
    return {"message": f"Agent '{agent_id}' disabled successfully"}

@router.get("/config/system", response_model=Dict[str, Any])
async def get_system_config(
    token_data: TokenData = Depends(get_token_data)
):
    """
    Get system-wide configuration (admin only)
    """
    check_admin_authorization(token_data)
    
    config = get_agent_config()
    system_config = {k: v for k, v in config.items() if k != "agents"}
    
    return system_config

@router.put("/config/system")
async def update_system_config(
    system_data: Dict[str, Any] = Body(...),
    token_data: TokenData = Depends(get_token_data)
):
    """
    Update system-wide configuration (admin only)
    
    Can update:
    - language_codes: Mapping of language names to codes
    - model_config: LLM model configuration
    - audio_options: Audio processing options
    - default_messages: Default system messages
    """
    check_admin_authorization(token_data)
    
    # Get current config
    config = get_agent_config()
    
    # Valid top-level config keys that can be updated
    valid_config_keys = ["language_codes", "model_config", "audio_options", "default_messages"]
    
    # Update config
    for key in valid_config_keys:
        if key in system_data:
            config[key] = system_data[key]
    
    # Save updated config
    update_agent_config(config)
    
    return {"message": "System configuration updated successfully"} 