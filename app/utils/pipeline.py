import os
from typing import Annotated, List, Dict, Any, Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from app.utils.agent_config import (
    get_agent_by_id, 
    get_language_codes,
    get_agent_model_config,
    get_agent_error_messages,
    get_agent_languages,
    get_audio_options
)

# Load environment variables
load_dotenv()

# Define valid agent types
AgentType = Literal["realestate", "hospital"]

# Get language codes from config
LANGUAGE_CODES = get_language_codes()

# Get audio options from config
AUDIO_OPTIONS = get_audio_options()

class ConversationState(TypedDict):
    """State definition for the conversation graph"""
    messages: Annotated[list, add_messages]  # Chat messages
    conversation_id: str  # Unique conversation ID
    detected_language: str  # Detected language from STT
    response: str  # Generated response to be sent to TTS
    history: List[Dict[str, Any]]  # Full conversation history
    agent_type: AgentType  # Type of agent to use

def format_ssml_response(text: str, language: str, agent_type: AgentType) -> str:
    """Format the response text with proper SSML tags
    
    Args:
        text: Raw response text
        language: Language code for SSML
        agent_type: Type of agent being used
        
    Returns:
        str: SSML formatted text
    """
    # Get agent-specific language settings
    agent_languages = get_agent_languages(agent_type)
    supported_languages = agent_languages.get("supported", [])
    primary_language = agent_languages.get("primary", "en-IN")
    
    # Get language code from mapping
    lang_code = LANGUAGE_CODES.get(language.lower(), primary_language)
    
    # Check if language is supported for this agent
    if lang_code not in supported_languages:
        # Use unsupported language message from agent config
        error_messages = get_agent_error_messages(agent_type)
        return error_messages.get("unsupported_language", f"<speak xml:lang='{primary_language}'><prosody rate='medium' pitch='0%'>Kindly please repeat.</prosody></speak>")
    
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

def create_agent(agent_type: AgentType):
    """Create and configure the conversation agent
    
    Args:
        agent_type: Type of agent to use
        
    Returns:
        compiled graph: The compiled agent graph
    """
    # Get agent-specific model configuration
    model_config = get_agent_model_config(agent_type)
    model_name = model_config.get("name", "claude-3-5-sonnet-20240620")
    temperature = model_config.get("temperature", 0.7)
    # Slightly higher temperature helps with handling unclear input
    if temperature < 0.6:
        temperature = 0.6
    provider = model_config.get("provider", "anthropic")
    
    # Initialize the LLM with model settings from config
    if provider.lower() == "anthropic":
        llm = ChatAnthropic(
            model=model_name,
            api_key=os.getenv('CLAUDE_API_KEY'),
            temperature=temperature
        )
    elif provider.lower() == "openai":
        llm = ChatOpenAI(
            model=model_name,
            api_key=os.getenv('OPENAI_API_KEY'),
            temperature=temperature
        )
    else:
        # Default to Anthropic if provider not recognized
        llm = ChatAnthropic(
            model=model_name,
            api_key=os.getenv('CLAUDE_API_KEY'),
            temperature=temperature
        )
    
    # Initialize the state graph
    graph = StateGraph(ConversationState)
    
    # Define the main conversation node
    def conversation_node(state: ConversationState):
        # Get conversation history and agent type
        history = state.get("history", [])
        current_agent_type = state.get("agent_type", agent_type)
        
        # Load appropriate system prompt
        system_prompt = load_prompt(current_agent_type)
        
        # Enhanced instruction for handling unclear input
        unclear_input_instruction = """
IMPORTANT: The speech-to-text transcription may sometimes produce unclear or incomplete text. 
When you receive input that seems unclear:
1. Look for keywords related to our services
2. Use conversation context to infer the likely meaning
3. Make reasonable assumptions based on common queries in this domain
4. When uncertain, respond to what you understood and ask for clarification
5. Be patient and helpful, even with fragmented or unclear queries
"""
        # system_prompt = system_prompt + "\n" + unclear_input_instruction
        
        # Add language enforcement instruction for the current detected language
        lang_instruction = f"""
IMPORTANT LANGUAGE INSTRUCTION: The user is speaking in {state["detected_language"]}. 
ALWAYS respond ONLY in {state["detected_language"]}. 
Do NOT use any other language in your response.
"""
        # system_prompt = system_prompt + "\n" + lang_instruction
        
        # Prepare messages with system prompt and conversation history
        messages = [
            SystemMessage(content=system_prompt),  # Always include system prompt first
        ]
        
        # Add conversation history (limited to last 20 exchanges for efficiency)
        recent_history = history[-50:] if len(history) > 50 else history
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
        ssml_response = format_ssml_response(
            response.content, 
            state["detected_language"], 
            current_agent_type
        )
        
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
            "agent_type": current_agent_type
        }
    
    # Add nodes and edges to the graph
    graph.add_node("conversation", conversation_node)
    graph.add_edge(START, "conversation")
    graph.add_edge("conversation", END)
    
    return graph.compile()

class Pipeline:
    """Main pipeline for handling voice agent conversations"""
    
    def __init__(self, anthropic_api_key: str = None, openai_api_key: str = None, agent_type: AgentType = "realestate"):
        """Initialize the pipeline
        
        Args:
            anthropic_api_key: API key for Anthropic (optional, defaults to env var)
            openai_api_key: API key for OpenAI (optional, defaults to env var)
            agent_type: Type of agent to use (realestate or hospital)
        """
        # Set API keys if provided
        if anthropic_api_key:
            os.environ['CLAUDE_API_KEY'] = anthropic_api_key
        if openai_api_key:
            os.environ['OPENAI_API_KEY'] = openai_api_key
            
        # Check for required API keys based on provider
        model_config = get_agent_model_config(agent_type)
        provider = model_config.get("provider", "anthropic")
        
        if provider.lower() == "anthropic" and not os.getenv('CLAUDE_API_KEY'):
            raise ValueError("Claude API key not provided but required for this agent")
        elif provider.lower() == "openai" and not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OpenAI API key not provided but required for this agent")
        
        self.agent_type = agent_type
        self.agent = create_agent(agent_type)
        self.conversation_histories = {}  # Store histories for each conversation
        self.current_language = {}  # Store current language for each conversation
        
    def get_error_message(self, error_type: str) -> str:
        """Get agent-specific error message
        
        Args:
            error_type: Type of error (error, unclear_audio, unsupported_language)
            
        Returns:
            str: SSML formatted error message
        """
        error_messages = get_agent_error_messages(self.agent_type)
        return error_messages.get(error_type, "I'm sorry, I couldn't understand. Please try again.")
        
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
        # Process extremely short inputs but add a note about it rather than rejecting
        if text and len(text.strip()) < 3:
            text = f"{text} [Note: Very short input received, attempting to process]"
            
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
        
        try:
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
        except Exception as e:
            # Return error message on failure
            return {
                "response": self.get_error_message("error", detected_language),
                "conversation_id": conversation_id,
                "detected_language": detected_language,
                "agent_type": self.agent_type,
                "error": str(e)
            }
        
    def clear_history(self, conversation_id: str) -> None:
        """Clear conversation history for a specific conversation
        
        Args:
            conversation_id: Unique conversation ID
        """
        conversation_key = f"{conversation_id}_{self.agent_type}"
        if conversation_key in self.conversation_histories:
            del self.conversation_histories[conversation_key]
        if conversation_key in self.current_language:
            del self.current_language[conversation_key]

# For testing the pipeline directly
if __name__ == "__main__":
    print("Interactive test mode. Type 'exit' to quit.")
    print("Available agent types: realestate, hospital")
    
    agent_type = input("Select agent type [realestate/hospital]: ").lower()
    if agent_type not in ["realestate", "hospital"]:
        agent_type = "realestate"
        print(f"Using default agent type: {agent_type}")
    
    language = input("Select language [english/hindi/telugu/tamil]: ").lower()
    if language not in LANGUAGE_CODES:
        language = "english"
        print(f"Using default language: {language}")
    
    # Create pipeline with selected agent type
    pipeline = Pipeline(agent_type=agent_type)
    conversation_id = "test"
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
            
        result = pipeline.process(
            text=user_input,
            conversation_id=conversation_id,
            detected_language=language
        )
        
        print(f"Bot [{agent_type}]: {result['response']}")