from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, UploadFile, File, Form, Request
from app.utils.auth import get_token_data
from app.schemas.schemas import (
    TokenData, OTPUsageResponse, AgentTrafficResponse,
    UsageListResponse, TrafficListResponse
)
from app.utils.agent_config import get_agent_config, update_agent_config, get_agent_by_id
from app.utils.prompt_manager import save_prompt_file
from typing import Dict, Any, List, Optional
from app.database.db import get_db
from app.models.models import get_otp_usages, get_agent_traffic
from datetime import datetime
import re
import os
from pathlib import Path
import glob
from fastapi.responses import FileResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  

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
    
    with get_db() as conn:
        # Get usage records with pagination
        usages, total_count = get_otp_usages(conn, limit=limit, offset=offset)
        
        # Convert to response objects
        usage_responses = [
            OTPUsageResponse(
                id=usage['id'],
                otp_id=usage['otp_id'],
                agent_type=usage['agent_type'],
                timestamp=usage['timestamp']
            ) for usage in usages
        ]
        
        # Clean up old records if we have too many (limit to 500)
        if total_count > 500:
            # Delete oldest records
            conn.execute(
                """
                DELETE FROM otp_usages
                WHERE id IN (
                    SELECT id FROM otp_usages
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
                """,
                (total_count - 500,)
            )
        
        return UsageListResponse(
            data=usage_responses,
            pagination={
                "total": min(total_count, 500),
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        )

@router.get("/traffic", response_model=TrafficListResponse)
async def get_agent_traffic_endpoint(
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
    
    with get_db() as conn:
        # Get traffic records with pagination
        traffic_data, total_count = get_agent_traffic(conn, limit=limit, offset=offset)
        
        # Convert to response objects
        traffic_responses = [
            AgentTrafficResponse(
                id=traffic['id'],
                agent_type=traffic['agent_type'],
                session_count=traffic['session_count'],
                last_activity=traffic['last_activity'],
                is_active=traffic['is_active']
            ) for traffic in traffic_data
        ]
        
        # Clean up old records if we have too many (limit to 500)
        if total_count > 500:
            # Delete oldest records
            conn.execute(
                """
                DELETE FROM agent_traffic
                WHERE id IN (
                    SELECT id FROM agent_traffic
                    ORDER BY last_activity ASC
                    LIMIT ?
                )
                """,
                (total_count - 500,)
            )
        
        return TrafficListResponse(
            data=traffic_responses,
            pagination={
                "total": min(total_count, 500),
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        )

@router.delete("/usage/clear")
async def clear_agent_usage(
    token_data: TokenData = Depends(get_token_data)
):
    """
    Clear all agent usage records (admin only)
    
    This operation cannot be undone.
    """
    check_admin_authorization(token_data)
    
    with get_db() as conn:
        # Count records before deletion
        count = conn.execute("SELECT COUNT(*) FROM otp_usages").fetchone()[0]
        
        # Delete all records
        conn.execute("DELETE FROM otp_usages")
        
        return {
            "success": True,
            "message": f"Successfully cleared {count} usage records"
        }

@router.delete("/traffic/clear")
async def clear_agent_traffic(
    token_data: TokenData = Depends(get_token_data)
):
    """
    Clear all agent traffic statistics (admin only)
    
    This operation cannot be undone.
    """
    check_admin_authorization(token_data)
    
    with get_db() as conn:
        # Count records before deletion
        count = conn.execute("SELECT COUNT(*) FROM agent_traffic").fetchone()[0]
        
        # Delete all records
        conn.execute("DELETE FROM agent_traffic")
        
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
    
    Optional fields:
    - can_interrupt: Whether the agent can be interrupted by the user (default: false)
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
        "enabled": True,
        "can_interrupt": agent_data.get("can_interrupt", False)
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
    - can_interrupt: Whether the agent can be interrupted (boolean)
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
    valid_fields = ["name", "description", "startup_message", "prompt", "enabled", "can_interrupt"]
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

@router.get("/recordings", response_model=List[Dict[str, Any]])
async def get_audio_recordings(
    token_data: TokenData = Depends(get_token_data),
):
    """
    Get list of audio recordings.
    Only accessible by admin users.
    """
    # Check admin authorization
    check_admin_authorization(token_data)
    
    try:
        # Path to recordings directory
        recordings_dir = "/home/ec2-user/voice-agent/voice-agent/audi_recordings"
        
        # Check if directory exists
        if not os.path.exists(recordings_dir):
            return []
            
        # Get all .wav files
        audio_files = glob.glob(os.path.join(recordings_dir, "*.wav"))
        
        # Format response
        result = []
        for file_path in audio_files:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            mod_time = os.path.getmtime(file_path)
            
            result.append({
                "file_name": file_name,
                "file_path": file_path,
                "size_bytes": file_size,
                "modified_time": mod_time
            })
            
        # Sort by modified time (newest first)
        result.sort(key=lambda x: x["modified_time"], reverse=True)
        
        return result
    except Exception as e:
        logger.error(f"Error fetching audio recordings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch audio recordings: {str(e)}",
        )

@router.get("/recordings/{file_name}")
async def get_audio_recording(
    file_name: str,
    token_data: TokenData = Depends(get_token_data),
):
    """
    Stream an audio recording file.
    Only accessible by admin users.
    """
    # Check admin authorization
    check_admin_authorization(token_data)
    
    try:
        recordings_dir = "audio_recordings"
        file_path = os.path.join(recordings_dir, file_name)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found"
            )
            
        return FileResponse(
            file_path, 
            media_type="audio/wav",
            filename=file_name
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming audio file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream audio file: {str(e)}",
        ) 