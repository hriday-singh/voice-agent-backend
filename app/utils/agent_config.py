from typing import Dict, List, Any, Optional
import json
import logging
from app.database.db import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database utility functions
def get_agent_config_from_db(session, agent_id: str) -> Optional[Dict[str, Any]]:
    """Get agent configuration from database"""
    try:
        from app.models.models import get_agent_config as get_agent_config_model
        
        agent_config = get_agent_config_model(session, agent_id)
        if not agent_config:
            return None
            
        return agent_config.model_dump()
    except Exception as e:
        logger.error(f"Error getting agent config from database: {str(e)}")
        return None

def get_global_config_from_db(session, key: str, default: Any = None) -> Any:
    """Get global configuration from database"""
    try:
        from app.models.models import get_global_config
        
        config_value = get_global_config(session, key)
        if config_value is None:
            return default
            
        return config_value
    except Exception as e:
        logger.error(f"Error getting global config from database: {str(e)}")
        return default

# JSON parsing helper
def parse_json_field(data: Any, field_name: str, default: Any = None) -> Any:
    """Parse JSON field if it's a string, otherwise return as is"""
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {field_name}")
            return default
    return data

# Agent configuration functions
def get_agent_config() -> Dict[str, Any]:
    """
    Get the agent configuration (legacy method)
    Returns: Complete agent configuration dictionary
    """
    with get_db() as session:
        try:
            from app.models.models import get_all_agent_configs, get_all_global_configs
            
            agents = {}
            agent_configs = get_all_agent_configs(session)
            
            for agent in agent_configs:
                agent_dict = agent.model_dump()
                agent_type = agent_dict.pop("agent_type")
                agents[agent_type] = agent_dict
            
            # Get global configs
            global_configs = get_all_global_configs(session)
            
            return {
                "agents": agents,
                **global_configs
            }
        except Exception as e:
            logger.error(f"Error loading agent config from database: {str(e)}")
            return {"agents": {}}

def update_agent_config(new_config: Dict[str, Any]) -> bool:
    """
    Update the agent configuration in the database
    
    Args:
        new_config: New configuration to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    with get_db() as session:
        try:
            from app.models.models import create_agent_config, set_global_config
            
            # Update agent configs
            if "agents" in new_config:
                for agent_id, agent_data in new_config["agents"].items():
                    # Add agent_type to the data
                    agent_data["agent_type"] = agent_id
                    create_agent_config(session, agent_data)
            
            # Update global configs
            for key in ["language_codes", "default_messages"]:
                if key in new_config:
                    set_global_config(session, key, new_config[key])
            
            return True
        except Exception as e:
            logger.error(f"Error updating agent config in database: {str(e)}")
            session.rollback()
            return False

def get_agent_by_agent_type(agent_type: str) -> Optional[Dict[str, Any]]:
    """
    Get agent configuration by agent_type
    Args:
        agent_type: Type of the agent to get
    Returns:
        Dict containing the agent configuration or None if not found
    """
    # Handle possible numeric ID values coming from the frontend
    if isinstance(agent_type, str) and agent_type.isdigit():
        logger.info(f"Numeric agent ID detected: {agent_type}, attempting to find by agent_type")
        
    logger.info(f"Looking up agent with agent_type: {agent_type}")
    with get_db() as session:
        agent_config = get_agent_config_from_db(session, agent_type)
        if agent_config:
            return agent_config
            
        # If not found and ID is numeric, check with int ID (AgentConfig.id)
        if isinstance(agent_type, str) and agent_type.isdigit():
            from app.models.models import AgentConfig
            from sqlmodel import select
            
            try:
                numeric_id = int(agent_type)
                agent = session.exec(select(AgentConfig).where(AgentConfig.id == numeric_id)).first()
                if agent:
                    logger.info(f"Found agent by numeric ID: {agent_type}, agent_type: {agent.agent_type}")
                    return get_agent_config_from_db(session, agent.agent_type)
            except Exception as e:
                logger.error(f"Error looking up agent by numeric ID: {e}")
        
        logger.warning(f"Agent not found with ID: {agent_type}")
        return None

def get_agent_by_id(agent_id: int) -> Optional[Dict[str, Any]]:
    """
    Get agent configuration by ID
    Args:
        agent_type: Type of the agent to get
    Returns:
        Dict containing the agent configuration or None if not found
    """
        
    logger.info(f"Looking up agent with agent_id: {agent_id}")
    with get_db() as session:
        agent_config = get_agent_config_from_db(session, agent_id)
        if agent_config:
            return agent_config
            
        # If not found and ID is numeric, check with int ID (AgentConfig.id)
        if isinstance(agent_id, str) and agent_id.isdigit():
            from app.models.models import AgentConfig
            from sqlmodel import select
            
            try:
                numeric_id = int(agent_id)
                agent = session.exec(select(AgentConfig).where(AgentConfig.id == numeric_id)).first()
                if agent:
                    logger.info(f"Found agent by numeric ID: {agent_id}, agent_type: {agent.agent_type}")
                    return get_agent_config_from_db(session, agent.agent_type)
            except Exception as e:
                logger.error(f"Error looking up agent by numeric ID: {e}")
        
        logger.warning(f"Agent not found with ID: {agent_id}")
        return None


def list_available_agents(include_disabled: bool = False) -> List[Dict[str, Any]]:
    """
    List all available agents
    Args:
        include_disabled: Whether to include disabled agents
    Returns:
        List of agent configurations formatted for the API
    """
    with get_db() as session:
        from app.models.models import get_all_agent_configs
        
        try:
            agent_configs = get_all_agent_configs(session)
            
            agents = []
            for agent in agent_configs:
                # Skip disabled agents unless explicitly requested
                if not include_disabled and not agent.enabled:
                    continue
                    
                # Get languages as a dictionary
                languages = agent.get_languages()
                
                agents.append({
                    "id": agent.agent_type,
                    "name": agent.name,
                    "description": agent.description,
                    "api_path": agent.api_path,
                    "is_outbound": agent.is_outbound,
                    "primary_language": languages.get("primary", "en-IN"),
                    "tags": agent.get_tags()
                })
            
            return agents
        except Exception as e:
            logger.error(f"Error listing agents from database: {str(e)}")
            agents = []
            
            return agents

def get_language_codes() -> Dict[str, str]:
    """Get language code mapping"""
    with get_db() as session:
        return get_global_config_from_db(session, "language_codes", {})

def get_agent_types() -> List[str]:
    """
    Get all valid agent types from the database
    
    Returns:
        List of agent type strings
    """
    with get_db() as session:
        try:
            from app.models.models import get_all_agent_configs
            
            agent_configs = get_all_agent_configs(session)
            return [agent.agent_type for agent in agent_configs]
        except Exception as e:
            logger.error(f"Error getting agent types from database: {str(e)}")
            # Default fallback values
            return ["realestate", "hospital"]

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
        
    languages = agent_config.get("languages", {})
    if isinstance(languages, str):
        try:
            import json
            return json.loads(languages)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in languages for agent {agent_id}")
            return {}
    
    return languages

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
        
    speech_context = agent_config.get("speech_context", [])
    
    # Ensure it's a list of strings, not JSON
    if isinstance(speech_context, str):
        try:
            return json.loads(speech_context)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in speech_context for agent {agent_id}")
            return []
    
    return speech_context

def get_agent_is_outbound(agent_id: str) -> bool:
    """
    Get the outbound setting for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        Boolean indicating if the agent allows outbound calls (default: False)
    """
    agent_config = get_agent_by_id(agent_id)
    if not agent_config:
        return False
    return agent_config.get("is_outbound", False)

def get_agent_model_config(agent_id: str) -> Dict[str, Any]:
    """
    Get model configuration for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        Dict containing model configuration or default config if not found
    """
    try:
        with get_db() as session:
            from app.models.models import get_agent_config as get_agent_config_model, get_llm_model
            
            agent_config = get_agent_config_model(session, agent_id)
            if not agent_config or not agent_config.llm_model_id:
                # Fallback to default configuration for Anthropic Claude
                return {
                    "provider": "anthropic",
                    "name": "claude-3-5-sonnet-20240620", 
                    "temperature": 0.7,
                    "display_name": "Claude 3.5 Sonnet"
                }
            
            # Get the model config
            model = get_llm_model(session, agent_config.llm_model_id)
            if not model:
                # Fallback to default configuration for Anthropic Claude
                return {
                    "provider": "anthropic",
                    "name": "claude-3-5-sonnet-20240620", 
                    "temperature": agent_config.temperature or 0.7,
                    "display_name": "Claude 3.5 Sonnet"
                }
            
            # Get provider info
            provider_name = model.provider.name if model.provider else "unknown"
            
            # Build model config with agent-specific temperature
            return {
                "provider": provider_name.lower(),
                "name": model.name,
                "temperature": agent_config.temperature,
                "display_name": model.display_name
            }
    except Exception as e:
        logger.error(f"Error getting model config for agent {agent_id}: {str(e)}")
        # Fallback to default configuration for Anthropic Claude
        return {
            "provider": "anthropic",
            "name": "claude-3-5-sonnet-20240620", 
            "temperature": 0.7,
            "display_name": "Claude 3.5 Sonnet"
        }

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
        with get_db() as session:
            return get_global_config_from_db(session, "default_messages", {})
    
    error_messages = agent_config["error_messages"]
    return parse_json_field(error_messages, f"error_messages for agent {agent_id}", {})

def get_default_messages() -> Dict[str, str]:
    """Get default error and system messages"""
    with get_db() as session:
        return get_global_config_from_db(session, "default_messages", {})

def get_agent_system_prompt(agent_id: str) -> str:
    """
    Get the system prompt for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        str: System prompt text or empty string if not found
    """
    with get_db() as session:
        from app.models.models import get_agent_system_prompt
        
        try:
            prompt = get_agent_system_prompt(session, agent_id)
            return prompt or ""
        except Exception as e:
            logger.error(f"Error getting system prompt for {agent_id}: {str(e)}")
            return ""

def update_agent_system_prompt(agent_id: str, system_prompt: str) -> bool:
    """
    Update the system prompt for a specific agent
    
    Args:
        agent_id: ID of the agent
        system_prompt: New system prompt text
        
    Returns:
        bool: True if successful, False otherwise
    """
    with get_db() as session:
        from app.models.models import update_agent_system_prompt
        
        try:
            return update_agent_system_prompt(session, agent_id, system_prompt)
        except Exception as e:
            logger.error(f"Error updating system prompt for {agent_id}: {str(e)}")
            return False

def get_agent_limitations(agent_id: str) -> List[str]:
    """
    Get limitations for a specific agent
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        List of limitation strings
    """
    try:
        agent_config = get_agent_by_id(agent_id)
        if not agent_config:
            return []
        
        limitations = agent_config.get("limitations", [])
        if isinstance(limitations, str):
            try:
                return json.loads(limitations)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in limitations for agent {agent_id}")
                return []
        
        return limitations
    except Exception as e:
        logger.error(f"Error getting limitations for agent {agent_id}: {str(e)}")
        return []

def update_agent_model_config(agent_id: str, model_config: Dict[str, Any]) -> bool:
    """
    Update the model configuration for a specific agent
    
    Args:
        agent_id: ID of the agent
        model_config: Dictionary containing model configuration
            {
                "provider": "anthropic",
                "name": "claude-3-sonnet",
                "temperature": 0.7
            }
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as session:
            from app.models.models import get_agent_config, update_agent_config
            
            # Get the agent config
            agent_config = get_agent_config(session, agent_id)
            if not agent_config:
                logger.error(f"Agent {agent_id} not found")
                return False
                
            # Get or create LLM model record
            from app.models.models import get_all_llm_providers, create_llm_provider, get_llm_provider
            from app.models.models import get_all_llm_models, create_llm_model
            
            # Get provider
            provider_name = model_config.get("provider", "anthropic").lower()
            providers = get_all_llm_providers(session)
            
            provider_id = None
            for provider in providers:
                if provider.name.lower() == provider_name:
                    provider_id = provider.id
                    break
                    
            # Create provider if it doesn't exist
            if not provider_id:
                provider_id = create_llm_provider(session, {
                    "name": provider_name.capitalize(),
                    "description": f"Auto-created provider for {provider_name}"
                })
                logger.info(f"Created new provider {provider_name} with ID {provider_id}")
                
            # Get model
            model_name = model_config.get("name", "claude-3-5-sonnet-20240620")
            models = get_all_llm_models(session, provider_id)
            
            model_id = None
            for model in models:
                if model.name == model_name:
                    model_id = model.id
                    break
                    
            # Create model if it doesn't exist
            if not model_id:
                display_name = model_config.get("display_name", model_name)
                default_temperature = model_config.get("temperature", 0.7)
                
                model_id = create_llm_model(session, {
                    "provider_id": provider_id,
                    "name": model_name,
                    "display_name": display_name,
                    "default_temperature": default_temperature
                })
                logger.info(f"Created new model {model_name} with ID {model_id}")
                
            # Update agent config with model ID and temperature
            updates = {
                "llm_model_id": model_id,
                "temperature": model_config.get("temperature", 0.7)
            }
            
            success = update_agent_config(session, agent_id, updates)
            return success
    except Exception as e:
        logger.error(f"Error updating model config for agent {agent_id}: {str(e)}")
        return False

def create_agent_config(config_data: Dict[str, Any]) -> Optional[int]:
    """
    Create a new agent configuration in the database
    
    Args:
        config_data: Dictionary containing agent configuration data
            Must include agent_type field
            
    Returns:
        int: ID of the created agent, or None if creation failed
    """
    try:
        with get_db() as session:
            from app.models.models import create_agent_config as create_agent_config_model
            
            # Validate required fields
            if "agent_type" not in config_data:
                logger.error("Missing required field 'agent_type' in agent configuration")
                return None
                
            # Handle JSON fields
            for field in ["languages", "speech_context", "limitations", "error_messages", "tags"]:
                if field in config_data and not isinstance(config_data[field], str):
                    try:
                        if isinstance(config_data[field], (dict, list)):
                            config_data[field] = json.dumps(config_data[field])
                        else:
                            # Convert to appropriate default format
                            if field in ["speech_context", "limitations", "tags"]:
                                config_data[field] = "[]"  # Empty list
                            else:
                                config_data[field] = "{}"  # Empty dict
                    except Exception as e:
                        logger.error(f"Error converting {field} to JSON: {e}")
                        # Set default values
                        if field in ["speech_context", "limitations", "tags"]:
                            config_data[field] = "[]"
                        else:
                            config_data[field] = "{}"
            
            # Create the agent configuration
            agent_id = create_agent_config_model(session, config_data)
            logger.info(f"Created new agent configuration with ID {agent_id}")
            return agent_id
            
    except Exception as e:
        logger.error(f"Error creating agent configuration: {str(e)}")
        return None 