from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Request
from app.utils.auth import get_token_data, verify_admin
from app.schemas.common import TokenData
from app.schemas.responses import UsageListResponse
from app.schemas.agent import (
    AgentConfigBase, AgentConfigCreate, 
    AgentConfigUpdate, AgentConfigResponse, GlobalConfigUpdate
)
from app.utils.agent_config import (
    get_agent_config, update_agent_config as update_config_util, get_agent_by_id, 
    list_available_agents, get_agent_system_prompt, update_agent_system_prompt, get_language_codes,
    get_agent_model_config, get_agent_error_messages,
    get_agent_languages
)
from app.utils.dynamic_agents import (
    register_agent,
    unregister_agent,
    get_active_agents,
    reload_agents
)
from typing import Dict, Any, List, Optional
from app.database.db import get_db
from app.models.models import (
    get_otp_usages, get_all_agent_configs, 
    get_agent_config_by_id, get_agent_config_as_dict_by_id,
    update_agent_config_by_id, delete_agent_config_by_id,
    get_all_global_configs, get_global_config, set_global_config, Session,
    OTPUsage, AgentConfig, update_agent_system_prompt_by_id, get_agent_system_prompt_by_id,
    get_agent_config as get_agent_config_model
)
import re
import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
from sqlmodel import select

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)  

# Main router for admin agent management
router = APIRouter(prefix="/admin/agents", tags=["Admin Agent Management"])
security = HTTPBearer()

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

# Usage-related endpoints
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
    
    with get_db() as session:
        # Get usage records with pagination
        usages, total_count = get_otp_usages(session, limit=limit, offset=offset)
        
        # Keep data capped at 500 records to prevent database growth
        if total_count > 500:
            # Get ids of records to delete (oldest first)
            all_usages = session.exec(select(OTPUsage).order_by(OTPUsage.timestamp)).all()
            records_to_delete = all_usages[:total_count-500]  # Get oldest records to delete
            
            # Delete them
            for usage in records_to_delete:
                session.delete(usage)
            
            session.commit()
            
            # Update total count
            total_count = 500
        
        return UsageListResponse(
            data=usages,
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
    
    with get_db() as session:
        # Count records before deletion
        all_usages = session.exec(select(OTPUsage)).all()
        count = len(all_usages)
        
        # Delete all records - get all and delete them one by one
        for usage in all_usages:
            session.delete(usage)
        
        session.commit()
        
        return {
            "success": True,
            "message": f"Successfully cleared {count} usage records"
        }

# Agent configuration endpoints
@router.get("/", response_model=List[Dict])
async def get_all_agent_configurations(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """
    Get a brief overview of all agent configurations
    
    Returns a list of agents with basic information suitable for displaying in a table or list view:
    - id: Database ID
    - agent_type: Unique type identifier
    - name: Display name
    - description: Brief description
    - enabled: Whether the agent is enabled
    - is_outbound: Whether the agent supports outbound calls
    """
    try:
        with get_db() as session:
            agent_configs = get_all_agent_configs(session)
            return [
                {
                    "id": agent.id,
                    "agent_type": agent.agent_type,
                    "name": agent.name,
                    "description": agent.description,
                    "enabled": agent.enabled,
                    "is_outbound": agent.is_outbound
                }
                for agent in agent_configs
            ]
    except Exception as e:
        logger.error(f"Error getting agent configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent configurations: {str(e)}"
        )

@router.get("/{agent_id}", response_model=Dict)
async def get_agent_configuration(
    agent_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """
    Get detailed information for a specific agent configuration by ID
    
    Returns comprehensive information about a single agent, including:
    - All basic information (id, name, description, etc.)
    - Voice settings (voice_name)
    - LLM settings (llm_model_id, temperature)
    - Languages and speech context
    - System prompt
    - Startup message
    - Error messages
    - Limitations
    - Timestamps
    
    Args:
        agent_id: The unique agent ID
    """
    with get_db() as session:
        agent_config = get_agent_config_as_dict_by_id(session, agent_id)
        if not agent_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent configuration with ID {agent_id} not found"
            )
            
        # Get the system prompt
        system_prompt = get_agent_system_prompt_by_id(session, agent_id)
        if system_prompt:
            agent_config["system_prompt"] = system_prompt
            
        return agent_config

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_agent_config(
    config: AgentConfigCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Create a new agent configuration in the database and register it with the system"""
    try:
        with get_db() as session:
            # Check if agent type already exists
            existing = get_agent_config_model(session, config.agent_type)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Agent with type {config.agent_type} already exists"
                )
                
            # Convert the pydantic model to a dict
            config_dict = config.model_dump()
            
            # Extract system prompt for separate storage if needed
            system_prompt = config_dict.get("system_prompt", "You are a helpful assistant for customer inquiries.")
            
            # Create the agent configuration using the utility function
            from app.utils.agent_config import create_agent_config
            config_id = create_agent_config(config_dict)
            
            if not config_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create agent configuration"
                )
            
            # Always register the agent regardless of enabled status
            try:
                if register_agent(config.agent_type):
                    logger.info(f"Agent '{config.agent_type}' automatically registered after creation")
                else:
                    logger.warning(f"Agent '{config.agent_type}' created but registration failed")
            except Exception as e:
                logger.error(f"Error during agent registration: {e}")
            
            return {
                "id": config_id, 
                "message": f"Agent configuration for {config.agent_type} created successfully",
                "registered": True
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent configuration: {str(e)}"
        )

@router.put("/{agent_id}")
async def update_existing_agent_config(
    agent_id: int,
    config: AgentConfigUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Update an existing agent configuration in the database by ID"""
    try:
        with get_db() as session:
            # Check if agent exists
            existing = get_agent_config_by_id(session, agent_id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent with ID {agent_id} not found"
                )
                
            # Convert the pydantic model to a dict
            config_dict = config.dict(exclude_unset=True)
            
            # Check if agent_type is being changed and validate uniqueness
            if "agent_type" in config_dict and config_dict["agent_type"] != existing.agent_type:
                # Check if the new agent_type already exists
                conflict = get_agent_config_model(session, config_dict["agent_type"])
                if conflict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Agent with type {config_dict['agent_type']} already exists"
                    )
            
            # Handle JSON fields
            if "languages" in config_dict and not isinstance(config_dict["languages"], str):
                config_dict["languages"] = json.dumps(config_dict["languages"])
                
            if "limitations" in config_dict and not isinstance(config_dict["limitations"], str):
                config_dict["limitations"] = json.dumps(config_dict["limitations"])
                
            if "error_messages" in config_dict and not isinstance(config_dict["error_messages"], str):
                config_dict["error_messages"] = json.dumps(config_dict["error_messages"])
                
            # Explicitly handle speech_context conversion to JSON
            if "speech_context" in config_dict:
                if isinstance(config_dict["speech_context"], list):
                    try:
                        config_dict["speech_context"] = json.dumps(config_dict["speech_context"])
                    except Exception as e:
                        logger.error(f"Error converting speech_context to JSON: {e}")
                        config_dict["speech_context"] = "[]"
            
            # Update the configuration
            success = update_agent_config_by_id(session, agent_id, config_dict)

            reload_agents()
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update agent configuration"
                )
                
            return {"message": f"Agent configuration with ID {agent_id} updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent configuration: {str(e)}"
        )

@router.delete("/{agent_id}")
async def delete_agent_config_endpoint(
    agent_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Delete an agent configuration from the database by ID and unregister it if active"""
    try:
        with get_db() as session:
            # Check if agent exists
            existing = get_agent_config_by_id(session, agent_id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent with ID {agent_id} not found"
                )
            
            # Get the agent type for unregistering
            agent_type = existing.agent_type if hasattr(existing, "agent_type") else str(agent_id)
            
            # Unregister the agent if it's active (errors are logged but won't stop deletion)
            try:
                unregister_agent(agent_type)
            except Exception as e:
                logger.error(f"Error unregistering agent '{agent_type}' during deletion: {e}")
                
            # Delete the configuration
            success = delete_agent_config_by_id(session, agent_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete agent configuration"
                )
                
            return {"message": f"Agent configuration with ID {agent_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent configuration: {str(e)}"
        )

@router.get("/{agent_id}/prompt", response_model=Dict[str, str])
async def get_agent_prompt(
    agent_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """
    Get the system prompt for an agent by ID
    
    Args:
        agent_id: ID of agent to get prompt for
    """
    with get_db() as session:
        agent_config = get_agent_config_by_id(session, agent_id)
        if not agent_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No agent found with ID {agent_id}"
            )
            
        system_prompt = get_agent_system_prompt_by_id(session, agent_id)
        if not system_prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No system prompt found for agent with ID {agent_id}"
            )
    
        return {
            "agent_id": agent_id,
            "agent_type": agent_config.agent_type,
            "system_prompt": system_prompt
        }

@router.put("/{agent_id}/prompt")
async def update_agent_prompt(
    agent_id: int,
    data: Dict[str, str] = Body(..., example={"system_prompt": "You are a helpful assistant..."}),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """
    Update the system prompt for an agent by ID
    
    Args:
        agent_id: ID of agent to update
        data: Request body containing the system_prompt field
    """
    if "system_prompt" not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing system_prompt field in request"
        )
    
    with get_db() as session:
        agent_config = get_agent_config_by_id(session, agent_id)
        if not agent_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No agent found with ID {agent_id}"
            )
            
        success = update_agent_system_prompt_by_id(session, agent_id, data["system_prompt"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update system prompt for agent with ID {agent_id}"
            )
    
        return {
            "message": f"Successfully updated system prompt for agent with ID {agent_id}",
            "agent_id": agent_id,
            "agent_type": agent_config.agent_type
        }

@router.put("/{agent_id}/enable")
async def enable_agent(
    agent_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """
    Enable an agent by ID
    
    Args:
        agent_id: ID of agent to enable
    """
    with get_db() as session:
        agent_config = get_agent_config_by_id(session, agent_id)
        if not agent_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No agent found with ID {agent_id}"
            )
            
        # Update enabled status
        success = update_agent_config_by_id(session, agent_id, {"enabled": True})
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to enable agent with ID {agent_id}"
            )
        
        # Register the agent
        agent_type = agent_config.agent_type if hasattr(agent_config, "agent_type") else str(agent_id)
    
        return {
            "message": f"Successfully enabled agent with ID {agent_id}",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "enabled": True
        }

@router.put("/{agent_id}/disable")
async def disable_agent(
    agent_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """
    Disable an agent by ID but keep it registered with the system
    
    Args:
        agent_id: ID of agent to disable
    """
    with get_db() as session:
        agent_config = get_agent_config_by_id(session, agent_id)
        if not agent_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No agent found with ID {agent_id}"
            )
            
        # Update enabled status
        success = update_agent_config_by_id(session, agent_id, {"enabled": False})
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to disable agent with ID {agent_id}"
            )

        agent_type = agent_config.agent_type if hasattr(agent_config, "agent_type") else str(agent_id)
    
        return {
            "message": f"Successfully disabled agent with ID {agent_id}",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "enabled": False
        }

# Global configuration endpoints
@router.get("/global-configs", response_model=Dict[str, Dict])
async def get_all_global_configurations(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Get all global configurations from the database"""
    try:
        with get_db() as session:
            global_configs = get_all_global_configs(session)
            return global_configs
    except Exception as e:
        logger.error(f"Error getting global configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve global configurations: {str(e)}"
        )

@router.get("/global-configs/language-codes", response_model=Dict[str, str])
async def get_language_codes_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """Get language codes from the database"""
    return get_language_codes()

@router.post("/global-configs")
async def save_global_configuration(
    config_data: Dict[str, Any] = Body(..., example={
        "key": "some_config_key",
        "value": "config_value",
        "description": "Description of the configuration"
    }),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_data: Dict = Depends(verify_admin)
):
    """
    Save or update a global configuration in the database
    
    Args:
        config_data: Dictionary containing:
            - key: Configuration key
            - value: Configuration value (can be any JSON-serializable type)
            - description: Optional description of the configuration
    """
    try:
        if "key" not in config_data or "value" not in config_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both 'key' and 'value' are required in the request body"
            )

        config_key = config_data["key"]
        config_value = config_data["value"]
        description = config_data.get("description", "")

        # Convert value to JSON string if it's not a primitive type
        if not isinstance(config_value, (str, int, float, bool)):
            config_value = json.dumps(config_value)

        with get_db() as session:
            # Try to update existing config or create new one
            success = set_global_config(
                session, 
                config_key, 
                config_value,
                description
            )

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to save global configuration for key: {config_key}"
                )

            return {
                "message": f"Successfully saved global configuration for key: {config_key}",
                "key": config_key,
                "value": config_value,
                "description": description
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving global configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save global configuration: {str(e)}"
        )