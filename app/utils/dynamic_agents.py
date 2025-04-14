from fastapi import FastAPI
from app.utils.agents.agent_base import VoiceAgent
import logging
from typing import Dict, Optional
from app.utils.langgraph import reload_agent_registry

logger = logging.getLogger(__name__)

# Store active agent instances and the FastAPI app
_active_agents: Dict[str, VoiceAgent] = {}
_fastapi_app: Optional[FastAPI] = None

def set_app(app: FastAPI) -> None:
    """
    Set the FastAPI app instance to use for all agent operations.
    Call this during app startup.
    
    Args:
        app: The FastAPI application instance
    """
    global _fastapi_app
    _fastapi_app = app
    logger.info("FastAPI app instance set for dynamic agent management")

def initialize_agents() -> None:
    """
    Initialize all agents from the database and mount them to the FastAPI app.
    Call this during app startup after set_app().
    This will load all agents regardless of their enabled status.
    """
    global _fastapi_app
    if not _fastapi_app:
        logger.error("FastAPI app not set. Call set_app() before initializing agents.")
        return

    from app.utils.agent_config import list_available_agents
    
    # Get all agents including disabled ones
    available_agents = list_available_agents(include_disabled=True)
    logger.info(f"Found {len(available_agents)} agents in database (including disabled)")
    
    # Initialize and mount each agent
    for agent in available_agents:
        agent_id = agent["id"]
        try:
            # Skip if already initialized
            if agent_id in _active_agents:
                logger.info(f"Agent '{agent_id}' already initialized, skipping")
                continue

            register_agent(agent_id)
            
        except Exception as e:
            logger.error(f"Failed to initialize agent '{agent_id}': {e}")

def register_agent(agent_id: str) -> bool:
    """
    Register and mount a new agent to the FastAPI app.
    
    Args:
        agent_id: The unique ID of the agent to register
        
    Returns:
        bool: True if agent was registered successfully, False otherwise
    """
    global _fastapi_app
    if not _fastapi_app:
        logger.error("FastAPI app not set. Call set_app() before registering agents.")
        return False

    # Skip if already registered
    if agent_id in _active_agents:
        logger.info(f"Agent '{agent_id}' already registered")
        return True
    
    try:
        # Reload the LangGraph agent registry to make sure it's up to date
        try:            
            reload_agent_registry()
            logger.info(f"LangGraph registry reloaded for agent '{agent_id}'")
        except Exception as e:
            logger.error(f"Error reloading LangGraph registry: {e}")
            # Continue anyway - we'll try to create the agent with existing registry
        
        # Create a new VoiceAgent instance
        try:
            agent = VoiceAgent(agent_type=agent_id)
        except Exception as e:
            logger.error(f"Error creating VoiceAgent instance for '{agent_id}': {e}")
            return False
        
        # Mount the agent's stream to the FastAPI app
        try:
            mount_path = f"/api/voice-agents/{agent_id}"
            agent.stream.mount(_fastapi_app, path=mount_path)
        except Exception as e:
            logger.error(f"Error mounting agent stream for '{agent_id}': {e}")
            return False
        
        # Store the agent instance
        _active_agents[agent_id] = agent
        
        logger.info(f"Successfully registered agent '{agent_id}' at path '{mount_path}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to register agent '{agent_id}': {e}")
        return False

def unregister_agent(agent_id: str) -> bool:
    """
    Unregister and unmount an agent from the FastAPI app.
    
    Args:
        agent_id: The unique ID of the agent to unregister
        
    Returns:
        bool: True if agent was unregistered successfully, False otherwise
    """
    global _fastapi_app
    if not _fastapi_app:
        logger.error("FastAPI app not set. Call set_app() before unregistering agents.")
        return False

    if agent_id not in _active_agents:
        logger.warning(f"Agent '{agent_id}' not found in active agents")
        return False
    
    try:
        # Get the agent instance
        agent = _active_agents[agent_id]
        
        # Unmount the agent's stream from the FastAPI app
        mount_path = f"/api/voice-agents/{agent_id}"
        # Note: There's no direct unmount method in FastAPI, so we need to remove the route
        # This is a bit hacky but works for FastAPI
        routes_to_remove = [
            route for route in _fastapi_app.routes 
            if getattr(route, "path", "").startswith(mount_path)
        ]
        
        for route in routes_to_remove:
            _fastapi_app.routes.remove(route)
        
        # Remove the agent from active agents
        del _active_agents[agent_id]
        
        logger.info(f"Successfully unregistered agent '{agent_id}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to unregister agent '{agent_id}': {e}")
        return False

def get_active_agents() -> Dict[str, str]:
    """
    Get a list of all active agents and their mount paths.
    
    Returns:
        Dict[str, str]: Dictionary mapping agent IDs to their mount paths
    """
    return {
        agent_id: f"/api/voice-agents/{agent_id}" 
        for agent_id in _active_agents.keys()
    }

def get_agent(agent_id: str) -> Optional[VoiceAgent]:
    """
    Get an active agent by ID.
    
    Args:
        agent_id: The unique ID of the agent
        
    Returns:
        Optional[VoiceAgent]: The agent instance if found, None otherwise
    """
    return _active_agents.get(agent_id)

def reload_agents() -> bool:
    """
    Reload all agents by unregistering and re-registering them.
    This is useful when an agent's configuration has been updated.
    
    Args:
        agent_id: The unique ID of the agent to reload
        
    Returns:
        bool: True if agent was reloaded successfully, False otherwise
    """
    logger.info(f"Reloading all agents")
    
    #unregister_agent(agent_id)
    # success = register_agent(agent_id)

    try:
        reload_agent_registry()
        logger.info(f"Successfully reloaded all agents")
        return True
    except Exception as e:
        logger.error(f"Error reloading LangGraph registry: {e}")
        return False
