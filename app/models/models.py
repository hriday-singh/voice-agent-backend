from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlmodel import Field, SQLModel, select, Session, JSON, Relationship
import json
from app.schemas.admin import AdminResponse
from app.schemas.otp import OTPResponse, OTPUsageResponse
from app.schemas.agent import AgentConfigResponse, GlobalConfigResponse, LLMProviderResponse, LLMModelResponse
import logging

logger = logging.getLogger(__name__)

# Define SQLModel models
class Admin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password_hash: str

class OTP(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True)
    max_uses: int = Field(default=5)
    remaining_uses: int = Field(default=5)
    is_used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

class OTPUsage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    otp_id: int = Field(foreign_key="otp.id", nullable=False)
    agent_type: str
    timestamp: datetime = Field(default_factory=datetime.now)

# Agent configuration models
class AgentConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_type: str = Field(unique=True, index=True)
    name: str
    description: str
    api_path: str
    startup_message: str
    system_prompt: str = Field(default="")
    enabled: bool = Field(default=True)
    voice_name: str
    is_outbound: bool = Field(default=False)
    languages: str = Field(default="{}", sa_type=JSON)
    speech_context: str = Field(default="[]", sa_type=JSON)
    llm_model_id: Optional[int] = Field(default=None, foreign_key="llmmodel.id")
    temperature: float = Field(default=0.7)
    limitations: str = Field(default="[]", sa_type=JSON)  # List of current limitations
    error_messages: str = Field(default="{}", sa_type=JSON)
    tags: str = Field(default="[]", sa_type=JSON)  # List of tags for the agent
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get_languages(self) -> Dict[str, Any]:
        """Get languages as a Python dictionary"""
        return json.loads(self.languages)
    
    def get_tags(self) -> List[str]:
        """Get tags as a Python list"""
        return json.loads(self.tags)
    
    def get_speech_context(self) -> List[str]:
        """Get speech context as a Python list"""
        # Handle empty values
        if not self.speech_context:
            return []
            
        # If it's already a list, return directly
        if isinstance(self.speech_context, list):
            return self.speech_context
            
        # Try parsing JSON string
        if self.speech_context.startswith('[') and self.speech_context.endswith(']'):
            try:
                return json.loads(self.speech_context)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in speech_context: {self.speech_context}")
                return []
                
        # Try using ast.literal_eval for Python literal parsing
        try:
            import ast
            return ast.literal_eval(self.speech_context)
        except (SyntaxError, ValueError):
            logger.error(f"Unable to parse speech_context: {self.speech_context}")
            return []
    
    def get_limitations(self) -> List[str]:
        """Get limitations as a Python list"""
        return json.loads(self.limitations)
    
    def get_error_messages(self) -> Dict[str, str]:
        """Get error messages as a Python dictionary"""
        return json.loads(self.error_messages)

class GlobalConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    config_key: str = Field(unique=True, index=True)
    config_value: str = Field(default="{}", sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
class LLMProvider(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # e.g., "Anthropic", "OpenAI", "Google"
    description: str = Field(default="")
    
    # Relationship with models
    models: List["LLMModel"] = Relationship(back_populates="provider")

class LLMModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    provider_id: int = Field(foreign_key="llmprovider.id")
    name: str  # e.g., "claude-3-5-sonnet", "gpt-4", "gemini-pro"
    display_name: str  # User-friendly display name
    default_temperature: float = Field(default=0.7)
    
    # Relationship with provider
    provider: LLMProvider = Relationship(back_populates="models")

# Admin model functions
def create_admin(session: Session, username: str, password_hash: str) -> int:
    """Create a new admin and return its ID"""
    admin = Admin(username=username, password_hash=password_hash)
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin.id

def get_admin_by_username(session: Session, username: str) -> Optional[Admin]:
    """Get admin by username"""
    admin = session.exec(select(Admin).where(Admin.username == username)).first()
    return admin

def update_admin_password(session: Session, admin_id: int, password_hash: str) -> bool:
    """Update admin password"""
    admin = session.get(Admin, admin_id)
    if not admin:
        return False
        
    admin.password_hash = password_hash
    session.add(admin)
    session.commit()
    return True

# OTP model functions
def create_otp(session: Session, code: str, max_uses: int = 5, expires_at: Optional[datetime] = None) -> int:
    """Create a new OTP and return its ID"""
    otp = OTP(
        code=code,
        max_uses=max_uses,
        remaining_uses=max_uses,
        expires_at=expires_at
    )
    session.add(otp)
    session.commit()
    session.refresh(otp)
    return otp.id

def get_otp_by_code(session: Session, code: str) -> Optional[OTPResponse]:
    """Get OTP by code"""
    otp = session.exec(select(OTP).where(OTP.code == code)).first()
    
    if not otp:
        return None
    
    return OTPResponse(
        id=otp.id,
        code=otp.code,
        max_uses=otp.max_uses,
        remaining_uses=otp.remaining_uses,
        is_used=otp.is_used,
        created_at=otp.created_at,
        expires_at=otp.expires_at
    )

def update_otp_usage(session: Session, otp_id: int) -> bool:
    """Update OTP usage count, setting is_used if no uses remain"""
    otp = session.get(OTP, otp_id)
    
    if not otp:
        return False
    
    otp.remaining_uses -= 1
    otp.is_used = otp.remaining_uses <= 0
    
    session.add(otp)
    session.commit()
    return True

def get_all_otps(session: Session, limit: int = 100, offset: int = 0) -> Tuple[List[OTPResponse], int]:
    """Get all OTPs with pagination, returns (otps, total_count)"""
    # Get total count - use len() with all() instead of count()
    all_otps = session.exec(select(OTP)).all()
    total = len(all_otps)
    
    # Get paginated results
    otps = session.exec(select(OTP).order_by(OTP.created_at.desc()).offset(offset).limit(limit)).all()
    
    result = []
    for otp in otps:
        result.append(OTPResponse(
            id=otp.id,
            code=otp.code,
            max_uses=otp.max_uses,
            remaining_uses=otp.remaining_uses,
            is_used=otp.is_used,
            created_at=otp.created_at,
            expires_at=otp.expires_at
        ))
    
    return result, total

# OTP Usage model functions
def record_otp_usage(session: Session, otp_id: int, agent_type: str) -> int:
    """Record OTP usage and return the usage ID"""
    usage = OTPUsage(otp_id=otp_id, agent_type=agent_type)
    session.add(usage)
    session.commit()
    session.refresh(usage)
    return usage.id

def get_otp_usages(session: Session, limit: int = 100, offset: int = 0) -> Tuple[List[OTPUsageResponse], int]:
    """Get OTP usages with pagination, returns (usages, total_count)"""
    # Get total count - use len() with all() instead of count()
    all_usages = session.exec(select(OTPUsage)).all()
    total = len(all_usages)
    
    # Get paginated results
    usages = session.exec(select(OTPUsage).order_by(OTPUsage.timestamp.desc()).offset(offset).limit(limit)).all()
    
    result = []
    for usage in usages:
        result.append(OTPUsageResponse(
            id=usage.id,
            otp_id=usage.otp_id,
            agent_type=usage.agent_type,
            timestamp=usage.timestamp
        ))
    
    return result, total

# Agent Configuration functions
def create_agent_config(session: Session, config_data: Dict[str, Any]) -> int:
    """Create or update an agent config and return its ID"""
    agent_type = config_data.get("agent_type")
    existing_config = session.exec(select(AgentConfig).where(AgentConfig.agent_type == agent_type)).first()
    
    # Handle JSON fields
    if "languages" in config_data and isinstance(config_data["languages"], dict):
        config_data["languages"] = json.dumps(config_data["languages"])
        
    # Handle speech_context - store as JSON string if it's a list
    if "speech_context" in config_data:
        if isinstance(config_data["speech_context"], list):
            try:
                config_data["speech_context"] = json.dumps(config_data["speech_context"])
            except Exception as e:
                logger.error(f"Error converting speech_context to JSON: {e}")
                config_data["speech_context"] = "[]"
    
    # Handle limitations - ensure it's stored as a JSON string of a list
    if "limitations" in config_data:
        if isinstance(config_data["limitations"], str):
            try:
                # Try to parse if it's a JSON string
                json.loads(config_data["limitations"])
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a single limitation
                config_data["limitations"] = json.dumps([config_data["limitations"]])
        elif isinstance(config_data["limitations"], list):
            config_data["limitations"] = json.dumps(config_data["limitations"])
        else:
            # Default to empty list for invalid types
            config_data["limitations"] = "[]"
    
    # Handle error_messages - keep as is if it's already a dict, otherwise convert to JSON string
    if "error_messages" in config_data and isinstance(config_data["error_messages"], dict):
        config_data["error_messages"] = json.dumps(config_data["error_messages"])
    
    # Handle tags - exactly like limitations
    if "tags" in config_data:
        if isinstance(config_data["tags"], str):
            try:
                # Try to parse if it's a JSON string
                json.loads(config_data["tags"])
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a single tag
                config_data["tags"] = json.dumps([config_data["tags"]])
        elif isinstance(config_data["tags"], list):
            config_data["tags"] = json.dumps(config_data["tags"])
        else:
            # Default to empty list for invalid types
            config_data["tags"] = "[]"
    
    if existing_config:
        # Update existing config
        for key, value in config_data.items():
            if hasattr(existing_config, key):
                setattr(existing_config, key, value)
        existing_config.updated_at = datetime.now()
        session.add(existing_config)
        session.commit()
        return existing_config.id
    else:
        # Create new config
        agent_config = AgentConfig(**config_data)
        session.add(agent_config)
        session.commit()
        session.refresh(agent_config)
        return agent_config.id

def get_agent_config(session: Session, agent_type: str) -> Optional[AgentConfig]:
    """Get agent configuration by type"""
    return session.exec(select(AgentConfig).where(AgentConfig.agent_type == agent_type)).first()

def get_agent_config_as_dict(session: Session, agent_type: str) -> Optional[Dict[str, Any]]:
    """Get agent configuration as a dictionary with JSON fields parsed"""
    agent_config = get_agent_config(session, agent_type)
    if not agent_config:
        return None
    
    result = {
        "id": agent_config.id,
        "agent_type": agent_config.agent_type,
        "name": agent_config.name,
        "description": agent_config.description,
        "api_path": agent_config.api_path,
        "startup_message": agent_config.startup_message,
        "system_prompt": agent_config.system_prompt,
        "enabled": agent_config.enabled,
        "voice_name": agent_config.voice_name,
        "is_outbound": agent_config.is_outbound,
        "languages": agent_config.get_languages(),
        "speech_context": agent_config.get_speech_context(),
        "limitations": agent_config.get_limitations(),
        "error_messages": agent_config.get_error_messages(),
        "tags": agent_config.get_tags(),
        "llm_model_id": agent_config.llm_model_id,
        "temperature": agent_config.temperature,
        "created_at": agent_config.created_at,
        "updated_at": agent_config.updated_at
    }
    
    return result

def get_all_agent_configs(session: Session) -> List[AgentConfig]:
    """Get all agent configurations"""
    return session.exec(select(AgentConfig).order_by(AgentConfig.agent_type)).all()

def get_all_agent_configs_as_dicts(session: Session) -> List[Dict[str, Any]]:
    """Get all agent configurations as dictionaries with JSON fields parsed"""
    agent_configs = get_all_agent_configs(session)
    return [agent_config_to_response(config) for config in agent_configs]

def update_agent_config(session: Session, agent_type: str, updates: Dict[str, Any]) -> bool:
    """Update an agent config and return success status"""
    agent_config = session.exec(select(AgentConfig).where(AgentConfig.agent_type == agent_type)).first()
    
    if not agent_config:
        return False
    
    # Handle JSON fields
    if "languages" in updates and isinstance(updates["languages"], dict):
        updates["languages"] = json.dumps(updates["languages"])
    
    # Handle speech_context - store as JSON string if it's a list
    if "speech_context" in updates:
        if isinstance(updates["speech_context"], list):
            try:
                updates["speech_context"] = json.dumps(updates["speech_context"])
            except Exception as e:
                logger.error(f"Error converting speech_context to JSON: {e}")
                updates["speech_context"] = "[]"
    
    # Handle limitations - ensure it's stored as a JSON string of a list
    if "limitations" in updates:
        if isinstance(updates["limitations"], str):
            try:
                # Try to parse if it's a JSON string
                json.loads(updates["limitations"])
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a single limitation
                updates["limitations"] = json.dumps([updates["limitations"]])
        elif isinstance(updates["limitations"], list):
            updates["limitations"] = json.dumps(updates["limitations"])
        else:
            # Default to empty list for invalid types
            updates["limitations"] = "[]"
    
    # Handle error_messages - keep as is if it's already a dict, otherwise convert to JSON string
    if "error_messages" in updates and isinstance(updates["error_messages"], dict):
        updates["error_messages"] = json.dumps(updates["error_messages"])
    
    # Handle tags - exactly like limitations
    if "tags" in updates:
        if isinstance(updates["tags"], str):
            try:
                # Try to parse if it's a JSON string
                json.loads(updates["tags"])
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a single tag
                updates["tags"] = json.dumps([updates["tags"]])
        elif isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])
        else:
            # Default to empty list for invalid types
            updates["tags"] = "[]"
    
    # Update timestamp
    updates["updated_at"] = datetime.now()
    
    # Update fields
    for key, value in updates.items():
        if hasattr(agent_config, key):
            setattr(agent_config, key, value)
    
    session.add(agent_config)
    session.commit()
    return True

def delete_agent_config(session: Session, agent_type: str) -> bool:
    """Delete agent configuration"""
    agent_config = session.exec(select(AgentConfig).where(AgentConfig.agent_type == agent_type)).first()
    
    if not agent_config:
        return False
    
    session.delete(agent_config)
    session.commit()
    return True

def update_agent_system_prompt(session: Session, agent_type: str, system_prompt: str) -> bool:
    """Update the system prompt for an agent
    
    Args:
        session: Database session
        agent_type: Type of agent to update
        system_prompt: New system prompt text
        
    Returns:
        bool: True if successful, False otherwise
    """
    agent_config = session.exec(select(AgentConfig).where(AgentConfig.agent_type == agent_type)).first()
    
    if not agent_config:
        return False
    
    agent_config.system_prompt = system_prompt
    agent_config.updated_at = datetime.now()
    session.add(agent_config)
    session.commit()
    return True

def get_agent_system_prompt(session: Session, agent_type: str) -> Optional[str]:
    """Get the system prompt for an agent
    
    Args:
        session: Database session
        agent_type: Type of agent
        
    Returns:
        str: System prompt text or None if not found
    """
    agent_config = session.exec(select(AgentConfig).where(AgentConfig.agent_type == agent_type)).first()
    
    if not agent_config:
        return None
            
    return agent_config.system_prompt

# Global configuration functions
def set_global_config(session: Session, key: str, value: Dict[str, Any]) -> int:
    """Set a global configuration value"""
    existing_config = session.exec(select(GlobalConfig).where(GlobalConfig.config_key == key)).first()
    
    # Convert dict to JSON string
    value_json = json.dumps(value)
    
    if existing_config:
        existing_config.config_value = value_json
        existing_config.updated_at = datetime.now()
        session.add(existing_config)
        session.commit()
        return existing_config.id
    else:
        global_config = GlobalConfig(config_key=key, config_value=value_json)
        session.add(global_config)
        session.commit()
        session.refresh(global_config)
        return global_config.id

def get_global_config(session: Session, key: str) -> Optional[Dict[str, Any]]:
    """Get a global configuration value"""
    config = session.exec(select(GlobalConfig).where(GlobalConfig.config_key == key)).first()
    if config:
        return json.loads(config.config_value) 
    return None

def get_all_global_configs(session: Session) -> Dict[str, Dict[str, Any]]:
    """Get all global configurations as a dictionary"""
    configs = session.exec(select(GlobalConfig)).all()
    return {config.config_key: json.loads(config.config_value) for config in configs}

# LLM Provider and Model functions
def get_all_llm_providers(session: Session) -> List[LLMProvider]:
    """Get all LLM providers"""
    return session.exec(select(LLMProvider).order_by(LLMProvider.name)).all()

def get_llm_provider(session: Session, provider_id: int) -> Optional[LLMProvider]:
    """Get an LLM provider by ID"""
    return session.exec(select(LLMProvider).where(LLMProvider.id == provider_id)).first()

def create_llm_provider(session: Session, provider_data: Dict[str, Any]) -> int:
    """Create a new LLM provider"""
    provider = LLMProvider(**provider_data)
    session.add(provider)
    session.commit()
    session.refresh(provider)
    return provider.id

def update_llm_provider(session: Session, provider_id: int, provider_data: Dict[str, Any]) -> bool:
    """Update an LLM provider"""
    provider = get_llm_provider(session, provider_id)
    if not provider:
        return False
    
    for key, value in provider_data.items():
        if hasattr(provider, key):
            setattr(provider, key, value)
    
    session.add(provider)
    session.commit()
    return True

def delete_llm_provider(session: Session, provider_id: int) -> bool:
    """Delete an LLM provider"""
    provider = get_llm_provider(session, provider_id)
    if not provider:
        return False
    
    # First need to delete all associated models
    models = session.exec(select(LLMModel).where(LLMModel.provider_id == provider_id)).all()
    for model in models:
        session.delete(model)
    
    session.delete(provider)
    session.commit()
    return True

def get_all_llm_models(session: Session, provider_id: Optional[int] = None) -> List[LLMModel]:
    """Get all LLM models, optionally filtered by provider"""
    if provider_id:
        return session.exec(select(LLMModel).where(LLMModel.provider_id == provider_id).order_by(LLMModel.name)).all()
    return session.exec(select(LLMModel).order_by(LLMModel.provider_id, LLMModel.name)).all()

def get_llm_model(session: Session, model_id: int) -> Optional[LLMModel]:
    """Get an LLM model by ID"""
    return session.exec(select(LLMModel).where(LLMModel.id == model_id)).first()

def create_llm_model(session: Session, model_data: Dict[str, Any]) -> int:
    """Create a new LLM model"""
    model = LLMModel(**model_data)
    session.add(model)
    session.commit()
    session.refresh(model)
    return model.id

def update_llm_model(session: Session, model_id: int, model_data: Dict[str, Any]) -> bool:
    """Update an LLM model"""
    model = get_llm_model(session, model_id)
    if not model:
        return False
    
    for key, value in model_data.items():
        if hasattr(model, key):
            setattr(model, key, value)
    
    session.add(model)
    session.commit()
    return True

def delete_llm_model(session: Session, model_id: int) -> bool:
    """Delete an LLM model"""
    model = get_llm_model(session, model_id)
    if not model:
        return False
    
    # Check if any agents are using this model
    agents_using_model = session.exec(select(AgentConfig).where(AgentConfig.llm_model_id == model_id)).all()
    if agents_using_model:
        # Update agents to use no model
        for agent in agents_using_model:
            agent.llm_model_id = None
            session.add(agent)
    
    session.delete(model)
    session.commit()
    return True

# Model conversion functions for API responses
def agent_config_to_response(agent_config: AgentConfig) -> Dict[str, Any]:
    """Convert an agent config to a response dictionary"""
    return {
        "id": agent_config.id,
        "agent_type": agent_config.agent_type,
        "name": agent_config.name,
        "description": agent_config.description,
        "api_path": agent_config.api_path,
        "startup_message": agent_config.startup_message,
        "system_prompt": agent_config.system_prompt,
        "enabled": agent_config.enabled,
        "voice_name": agent_config.voice_name,
        "is_outbound": agent_config.is_outbound,
        "languages": agent_config.get_languages(),
        "speech_context": agent_config.get_speech_context(),
        "limitations": agent_config.get_limitations(),
        "error_messages": agent_config.get_error_messages(),
        "tags": agent_config.get_tags(),
        "llm_model_id": agent_config.llm_model_id,
        "temperature": agent_config.temperature,
        "created_at": agent_config.created_at,
        "updated_at": agent_config.updated_at
    }

def agent_configs_to_responses(configs: List[AgentConfig]) -> List[Dict[str, Any]]:
    """Convert a list of AgentConfig to response dicts"""
    return [
        {
            "id": config.id,
            "agent_type": config.agent_type,
            "name": config.name,
            "description": config.description,
            "api_path": config.api_path,
            "startup_message": config.startup_message,
            "system_prompt": config.system_prompt,
            "enabled": config.enabled,
            "voice_name": config.voice_name,
            "is_outbound": config.is_outbound,
            "languages": config.get_languages(),
            "speech_context": config.get_speech_context(),
            "limitations": config.get_limitations(),
            "error_messages": config.get_error_messages(),
            "tags": config.get_tags(),
            "llm_model_id": config.llm_model_id,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }
        for config in configs
    ]

def get_agent_config_by_id(session: Session, agent_id: int) -> Optional[AgentConfig]:
    """Get agent configuration by ID"""
    return session.get(AgentConfig, agent_id)

def get_agent_config_as_dict_by_id(session: Session, agent_id: int) -> Optional[Dict[str, Any]]:
    """Get agent configuration as a dictionary with JSON fields parsed by ID"""
    agent_config = get_agent_config_by_id(session, agent_id)
    if not agent_config:
        return None
    
    return agent_config_to_response(agent_config)

def update_agent_config_by_id(session: Session, agent_id: int, updates: Dict[str, Any]) -> bool:
    """Update an agent config by ID and return success status"""
    agent_config = get_agent_config_by_id(session, agent_id)
    
    if not agent_config:
        return False
    
    # Handle JSON fields
    if "languages" in updates and isinstance(updates["languages"], dict):
        updates["languages"] = json.dumps(updates["languages"])
    
    # Handle speech_context - store as JSON string if it's a list
    if "speech_context" in updates:
        if isinstance(updates["speech_context"], list):
            try:
                updates["speech_context"] = json.dumps(updates["speech_context"])
            except Exception as e:
                logger.error(f"Error converting speech_context to JSON: {e}")
                updates["speech_context"] = "[]"
    
    if "llm_config" in updates and isinstance(updates["llm_config"], dict):
        updates["llm_config"] = json.dumps(updates["llm_config"])
    
    # Handle limitations - ensure it's stored as a JSON string of a list
    if "limitations" in updates:
        if isinstance(updates["limitations"], str):
            try:
                # Try to parse if it's a JSON string
                json.loads(updates["limitations"])
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a single limitation
                updates["limitations"] = json.dumps([updates["limitations"]])
        elif isinstance(updates["limitations"], list):
            updates["limitations"] = json.dumps(updates["limitations"])
        else:
            # Default to empty list for invalid types
            updates["limitations"] = "[]"
    
    # Handle error_messages - keep as is if it's already a dict, otherwise convert to JSON string
    if "error_messages" in updates and isinstance(updates["error_messages"], dict):
        updates["error_messages"] = json.dumps(updates["error_messages"])
    
    # Handle tags - exactly like limitations
    if "tags" in updates:
        if isinstance(updates["tags"], str):
            try:
                # Try to parse if it's a JSON string
                json.loads(updates["tags"])
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a single tag
                updates["tags"] = json.dumps([updates["tags"]])
        elif isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])
        else:
            # Default to empty list for invalid types
            updates["tags"] = "[]"
    
    # Update timestamp
    updates["updated_at"] = datetime.now()
    
    # Update fields
    for key, value in updates.items():
        if hasattr(agent_config, key):
            setattr(agent_config, key, value)
    
    session.add(agent_config)
    session.commit()
    return True

def delete_agent_config_by_id(session: Session, agent_id: int) -> bool:
    """Delete agent configuration by ID"""
    agent_config = get_agent_config_by_id(session, agent_id)
    
    if not agent_config:
        return False
    
    session.delete(agent_config)
    session.commit()
    return True

def update_agent_system_prompt_by_id(session: Session, agent_id: int, system_prompt: str) -> bool:
    """Update the system prompt for an agent by ID
    
    Args:
        session: Database session
        agent_id: ID of agent to update
        system_prompt: New system prompt text
        
    Returns:
        bool: True if successful, False otherwise
    """
    agent_config = get_agent_config_by_id(session, agent_id)
    
    if not agent_config:
        return False
    
    agent_config.system_prompt = system_prompt
    agent_config.updated_at = datetime.now()
    session.add(agent_config)
    session.commit()
    return True

def get_agent_system_prompt_by_id(session: Session, agent_id: int) -> Optional[str]:
    """Get the system prompt for an agent by ID
    
    Args:
        session: Database session
        agent_id: ID of agent
        
    Returns:
        str: System prompt text or None if not found
    """
    agent_config = get_agent_config_by_id(session, agent_id)
    
    if not agent_config:
        return None
            
    return agent_config.system_prompt
