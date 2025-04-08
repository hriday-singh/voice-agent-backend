import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the JSON config file
CONFIG_FILE_PATH = Path(__file__).parent / "agent_configs.json"

# Cache for the loaded config to avoid multiple file reads
_config_cache = None

def get_agent_config() -> Dict[str, Any]:
    """
    Get the agent configuration from the JSON file
    Returns: Complete agent configuration dictionary
    """
    global _config_cache
    
    # Return cached config if available
    if _config_cache is not None:
        return _config_cache
    
    # Load config from JSON file
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
        return _config_cache
    except Exception as e:
        # Fallback to empty config if file can't be loaded
        logger.error(f"Error loading agent config: {str(e)}")
        _config_cache = {"agents": {}}
        return _config_cache

def update_agent_config(new_config: Dict[str, Any]) -> bool:
    """
    Update the agent configuration in the JSON file
    
    Args:
        new_config: New configuration to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    global _config_cache
    
    try:
        # Create a backup of the current config if it exists
        if CONFIG_FILE_PATH.exists():
            backup_path = CONFIG_FILE_PATH.with_suffix(".json.bak")
            CONFIG_FILE_PATH.rename(backup_path)
        
        # Write the new config
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2)
        
        # Update the cache
        _config_cache = new_config
        
        return True
    except Exception as e:
        logger.error(f"Error updating agent config: {str(e)}")
        # Try to restore from backup if update failed
        if backup_path.exists():
            try:
                backup_path.rename(CONFIG_FILE_PATH)
            except:
                pass
        return False

def get_agent_by_id(agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get agent configuration by ID
    Args:
        agent_id: ID of the agent to get
    Returns:
        Dict containing the agent configuration or None if not found
    """
    config = get_agent_config()
    return config["agents"].get(agent_id, None)

def list_available_agents(include_disabled: bool = False) -> List[Dict[str, Any]]:
    """
    List all available agents
    Args:
        include_disabled: Whether to include disabled agents
    Returns:
        List of agent configurations formatted for the API
    """
    config = get_agent_config()
    
    agents = []
    for agent_id, agent_info in config["agents"].items():
        # Skip disabled agents unless explicitly requested
        if not include_disabled and agent_info.get("enabled", True) is False:
            continue
            
        agents.append({
            "id": agent_id,
            "name": agent_info["name"],
            "description": agent_info["description"],
            "api_path": agent_info["api_path"]
        })
    
    return agents

def get_language_codes() -> Dict[str, str]:
    """Get language code mapping"""
    config = get_agent_config()
    return config.get("language_codes", {})

def get_agent_languages(agent_id: str) -> Dict[str, Any]:
    """
    Get language settings for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        Dict containing language settings or empty dict if not found
    """
    agent_config = get_agent_by_id(agent_id)
    if not agent_config:
        return {}
    return agent_config.get("languages", {})

def get_agent_speech_context(agent_id: str) -> List[str]:
    """
    Get speech context phrases for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        List of phrases to improve speech recognition, or empty list if not found
    """
    agent_config = get_agent_by_id(agent_id)
    if not agent_config:
        return []
    return agent_config.get("speech_context", [])

def get_agent_can_interrupt(agent_id: str) -> bool:
    """
    Get the interrupt setting for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        Boolean indicating if the agent allows interruptions (default: False)
    """
    agent_config = get_agent_by_id(agent_id)
    if not agent_config:
        return False
    return agent_config.get("can_interrupt", False)

def get_agent_model_config(agent_id: str) -> Dict[str, Any]:
    """
    Get model configuration for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        Dict containing model configuration or default config if not found
    """
    agent_config = get_agent_by_id(agent_id)
    if not agent_config or "model_config" not in agent_config:
        # Fallback to global config
        config = get_agent_config()
        return config.get("model_config", {})
    return agent_config["model_config"]

def get_agent_error_messages(agent_id: str) -> Dict[str, str]:
    """
    Get error messages for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        Dict containing error messages or default messages if not found
    """
    agent_config = get_agent_by_id(agent_id)
    if not agent_config or "error_messages" not in agent_config:
        # Fallback to default messages
        config = get_agent_config()
        return config.get("default_messages", {})
    return agent_config["error_messages"]

def get_audio_options() -> Dict[str, float]:
    """Get audio processing options"""
    config = get_agent_config()
    return config.get("audio_options", {})

def get_default_messages() -> Dict[str, str]:
    """Get default error and system messages"""
    config = get_agent_config()
    return config.get("default_messages", {}) 