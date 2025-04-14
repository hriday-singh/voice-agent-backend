from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class AgentUsage(BaseModel):
    agent_type: str

class AgentConfigBase(BaseModel):
    name: str
    description: str
    api_path: str
    startup_message: str
    system_prompt: str = ""
    enabled: bool = True
    voice_name: str
    is_outbound: bool = False
    languages: Dict
    speech_context: List[str]
    limitations: List[str] = []
    llm_model_id: Optional[int] = None
    temperature: float = 0.7
    error_messages: Dict
    tags: List[str] = []

class AgentConfigCreate(AgentConfigBase):
    agent_type: str

class AgentConfigUpdate(AgentConfigBase):
    pass

class AgentConfigResponse(AgentConfigBase):
    id: int
    agent_type: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GlobalConfigBase(BaseModel):
    config_key: str
    config_value: Dict[str, Any]

class GlobalConfigCreate(GlobalConfigBase):
    pass

class GlobalConfigUpdate(BaseModel):
    config_value: Dict[str, Any]

class GlobalConfigResponse(GlobalConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    agent_type: str

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# LLM Provider and Model Schemas
class LLMProviderBase(BaseModel):
    name: str
    description: str = ""

class LLMProviderCreate(LLMProviderBase):
    pass

class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class LLMProviderResponse(LLMProviderBase):
    id: int
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

class LLMModelBase(BaseModel):
    provider_id: int
    name: str
    display_name: str
    default_temperature: float = 0.7

class LLMModelCreate(LLMModelBase):
    pass

class LLMModelUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    default_temperature: Optional[float] = None

class LLMModelResponse(LLMModelBase):
    id: int
    provider_id: int
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True 