import os
from typing import List, TypedDict, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
import logging
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Simple state definition
class AgentState(TypedDict):
    messages: List[BaseMessage]

# Basic agent configuration
class AgentConfig(TypedDict):
    agent_id: str
    system_prompt: str
    model_name: str
    model_provider: str
    temperature: float

# Load agent definitions from database
def load_agent_definitions():
    """
    Loads agent configurations from the database.
    """
    from app.utils.agent_config import list_available_agents, get_agent_system_prompt, get_agent_model_config
    
    agents_list = []
    
    # Get all available agents (enabled only)
    available_agents = list_available_agents(include_disabled=False)
    
    for agent in available_agents:
        agent_id = agent["id"]
        
        # Get system prompt and model config
        system_prompt = get_agent_system_prompt(agent_id)
        model_config = get_agent_model_config(agent_id)
        
        # Create agent config
        agent_config = {
            "agent_id": agent_id,
            "system_prompt": system_prompt,
            "model_provider": model_config.get("provider", "openai"),
            "model_name": model_config.get("name", "gpt-3.5-turbo"),
            "temperature": model_config.get("temperature", 0.7)
        }
        
        agents_list.append(agent_config)  
    return agents_list

# Initialize agent registry
AGENT_REGISTRY = {agent['agent_id']: agent for agent in load_agent_definitions()}

# Node function
def agent_node(state: AgentState, config: RunnableConfig):
    """LangGraph node that calls the appropriate LLM based on agent config."""
    # Get agent config from the configurable
    agent_config = config['configurable'].get('agent_config', {})
    agent_id = agent_config.get('agent_id', 'unknown')
    
    # Extract model details
    provider = agent_config.get('model_provider', 'openai').lower()
    model_name = agent_config.get('model_name', 'gpt-3.5-turbo')
    system_prompt = agent_config.get('system_prompt', 'You are a helpful assistant. Only respoond in SSML format.')
    temperature = agent_config.get('temperature', 0.7)
    
    # Create the appropriate LLM based on provider
    try:
        if provider == 'openai':
            llm = ChatOpenAI(model=model_name, temperature=temperature)
        elif provider == 'anthropic':
            api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            llm = ChatAnthropic(model=model_name, temperature=temperature, api_key=api_key)
        elif provider in ['google', 'gemini']:
            api_key = os.getenv("GEMINI_API_KEY")
            llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature, api_key=api_key)
        else:
            # Default to OpenAI if provider not recognized
            llm = ChatOpenAI(model=model_name, temperature=temperature)
    except Exception:
        # Fallback to OpenAI on any error
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
    
    # Create the prompt
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages")
    ])

    prompt = prompt_template.invoke(state)
    response = llm.invoke(prompt)
    return {"messages": [response]}


# Build the graph
builder = StateGraph(AgentState)
builder.add_node('model',action=agent_node)
builder.add_edge(START,'model')
# builder.add_node("agent", agent_node)
# builder.set_entry_point("agent")
# builder.add_edge("agent", END)

memory = MemorySaver()

# Compile the graph
graph = builder.compile(checkpointer=memory)

def ensure_ssml_format(text: str) -> str:
    """
    Ensures the text is properly formatted as SSML.
    
    This function efficiently validates and corrects SSML markup to ensure it's correctly
    formatted for speech synthesis services.
    
    Args:
        text: The text that may or may not contain SSML markup
        
    Returns:
        Properly formatted SSML string
    """
    # Remove ```xml and ``` tags that might come from LLM responses
    text = re.sub(r'```xml\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    
    # If already has speak tags, return as is
    if re.search(r'^\s*<speak.*?>.*?</speak>\s*$', text, re.DOTALL):
        return text
    
    # If no speak tags, wrap in speak tags
    return f"<speak>{text}</speak>"

# Function to get agent responses
def get_agent_response(agent_id: str, user_input: str, conversation_id: str) -> str:
    """Get a response from an agent."""
    # Get the agent configuration
    agent_config = AGENT_REGISTRY.get(agent_id)
    if not agent_config:
        return f"Error: Agent '{agent_id}' not found."
    
    # Create input with the user's message
    input_messages = {"messages": [HumanMessage(content=user_input)]}

    
    # Set up configuration with thread_id and agent_config
    config = {
        "configurable": {
            "thread_id": conversation_id,
            "agent_config": agent_config
        }
    }

    try:
        # Run the graph
        output_state = graph.invoke(input_messages, config)
       
        # Extract the AI message
        if output_state and "messages" in output_state and output_state["messages"]:
            ai_message = output_state["messages"][-1]
            if hasattr(ai_message, "content"):
                response_content = ai_message.content
                # Format as SSML if needed
                ssml_formatted_response = ensure_ssml_format(response_content)
                return ssml_formatted_response
        
        return "<speak>No response generated.</speak>"
    except Exception as e:
        return f"<speak>Error: {str(e)}</speak>"

def reload_agent_registry():
    """Reload the agent registry."""
    global AGENT_REGISTRY
    AGENT_REGISTRY = {agent['agent_id']: agent for agent in load_agent_definitions()}
    return len(AGENT_REGISTRY)