import os
from typing import Annotated, List, Dict, Any, Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from app.utils.agent_config import get_agent_by_id, get_language_codes

# Load environment variables
load_dotenv()

# Define valid agent types
AgentType = Literal["realestate", "hospital"]

# Get language codes from config
LANGUAGE_CODES = get_language_codes()

# Get model configuration from central config
# MODEL_CONFIG = get_model_config()
# MODEL_NAME = MODEL_CONFIG.get("name", "gpt-4o")
MODEL_NAME = "claude-3-5-sonnet-20240620"
TEMPERATURE = 0.7

class ConversationState(TypedDict):
    """State definition for the conversation graph"""
    messages: Annotated[list, add_messages]  # Chat messages
    conversation_id: str  # Unique conversation ID
    detected_language: str  # Detected language from STT
    response: str  # Generated response to be sent to TTS
    history: List[Dict[str, Any]]  # Full conversation history
    agent_type: AgentType  # Type of agent to use

def format_ssml_response(text: str, language: str) -> str:
    """Format the response text with proper SSML tags
    
    Args:
        text: Raw response text
        language: Language code for SSML
        
    Returns:
        str: SSML formatted text
    """
    # Get language code from mapping
    lang_code = LANGUAGE_CODES.get(language.lower(), "en-IN")
    
    # Check if text already has SSML tags
    if text.strip().startswith('<speak>') and text.strip().endswith('</speak>'):
        # Ensure language tag is present
        if f'xml:lang="{lang_code}"' not in text:
            text = text.replace('<speak>', f'<speak xml:lang="{lang_code}">')
        return text
    
    # Add SSML tags with proper language
    ssml = f"""<speak xml:lang="{lang_code}">
    <prosody rate="medium" pitch="0%">{text}</prosody>
</speak>"""
    
    return ssml

def load_prompt(agent_type: AgentType) -> str:
    """Load system prompt for the specified agent type
    
    Args:
        agent_type: Type of agent to use
        
    Returns:
        str: System prompt for the agent
    """
    try:
        # Get agent configuration
        agent_config = get_agent_by_id(agent_type)
        if not agent_config or "prompt_file" not in agent_config:
            # Fallback to simple prompt if agent not found
            return f"You are a helpful assistant for {agent_type} inquiries."
            
        # Load prompt from file path in config
        prompt_path = agent_config["prompt_file"]
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        # Fallback to simple prompt if file can't be loaded
        return f"You are a helpful assistant for {agent_type} inquiries."

def create_agent():
    """Create and configure the conversation agent
    
    Returns:
        compiled graph: The compiled agent graph
    """
    # Initialize the LLM with model settings from config
    llm = ChatAnthropic(
        model=MODEL_NAME,
        api_key=os.getenv('CLAUDE_API_KEY'),
        temperature=TEMPERATURE
    )
    # llm = ChatOpenAI(
    #     model=MODEL_NAME,
    #     api_key=os.getenv('OPENAI_API_KEY'),
    #     temperature=TEMPERATURE
    # )
    
    # Initialize the state graph
    graph = StateGraph(ConversationState)
    
    # Define the main conversation node
    def conversation_node(state: ConversationState):
        # Get conversation history and agent type
        history = state.get("history", [])
        agent_type = state.get("agent_type", "realestate")
        
        # Load appropriate system prompt
        system_prompt = load_prompt(agent_type)
        
        # Prepare messages with system prompt and conversation history
        messages = [
            SystemMessage(content=system_prompt),  # Always include system prompt first
        ]
        
        # Add conversation history (limited to last 10 exchanges for efficiency)
        recent_history = history[-30:] if len(history) > 30 else history
        for msg in recent_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current message
        messages.extend(state["messages"])
        
        # Get response from LLM
        response = llm.invoke(messages)
        
        # Format response with SSML
        ssml_response = format_ssml_response(response.content, state["detected_language"])
        
        # Update history with current exchange
        new_history = history + [
            {"role": "user", "content": state["messages"][0].content},
            {"role": "assistant", "content": response.content}
        ]
        
        # Update state with response and history
        return {
            "messages": response,
            "response": ssml_response,
            "conversation_id": state["conversation_id"],
            "detected_language": state["detected_language"],
            "history": new_history,
            "agent_type": agent_type
        }
    
    # Add nodes and edges to the graph
    graph.add_node("conversation", conversation_node)
    graph.add_edge(START, "conversation")
    graph.add_edge("conversation", END)
    
    return graph.compile()

class Pipeline:
    """Main pipeline for handling voice agent conversations"""
    
    def __init__(self, anthropic_api_key: str = None, agent_type: AgentType = "realestate"):
        """Initialize the pipeline
        
        Args:
            anthropic_api_key: API key for Anthropic (optional, defaults to env var)
            agent_type: Type of agent to use (realestate or hospital)
        """
        if anthropic_api_key:
            os.environ['CLAUDE_API_KEY'] = anthropic_api_key
        elif not os.getenv('CLAUDE_API_KEY'):
            raise ValueError("Claude API key not provided")
        
        self.agent_type = agent_type
        self.agent = create_agent()
        self.conversation_histories = {}  # Store histories for each conversation
        
    def process(self, 
                text: str, 
                conversation_id: str, 
                detected_language: str = "english") -> Dict[str, Any]:
        """Process incoming text and generate response
        
        Args:
            text: Transcribed text from STT
            conversation_id: Unique conversation ID
            detected_language: Detected language from STT
            
        Returns:
            dict: Contains response text and other metadata
        """
        # Get existing history or initialize new one
        conversation_key = f"{conversation_id}_{self.agent_type}"
        history = self.conversation_histories.get(conversation_key, [])
        
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=text)],
            "conversation_id": conversation_id,
            "detected_language": detected_language,
            "response": "",
            "history": history,
            "agent_type": self.agent_type
        }
        
        # Run the agent
        final_state = self.agent.invoke(initial_state)
        
        # Update conversation history
        self.conversation_histories[conversation_key] = final_state["history"]
        
        # Return the response
        return {
            "response": final_state["response"],
            "conversation_id": final_state["conversation_id"],
            "detected_language": final_state["detected_language"],
            "agent_type": final_state["agent_type"]
        }
        
    def clear_history(self, conversation_id: str) -> None:
        """Clear conversation history for a specific conversation
        
        Args:
            conversation_id: Unique conversation ID
        """
        conversation_key = f"{conversation_id}_{self.agent_type}"
        if conversation_key in self.conversation_histories:
            del self.conversation_histories[conversation_key]