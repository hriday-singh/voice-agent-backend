from app.utils.speech_service import get_stt_model, get_tts_model
from app.utils.pipeline import Pipeline
from app.utils.agent_config import get_agent_by_id
from decouple import config
from fastrtc import ReplyOnPause, AlgoOptions, Stream
from uuid import uuid4

# Get agent configuration
agent_config = get_agent_by_id("realestate")

# Initialize models
stt_model = get_stt_model()
tts_model = get_tts_model()

# Set voice name if specified in config
if agent_config and "voice_name" in agent_config:
    tts_model.set_voice_name(agent_config["voice_name"])

# Initialize pipeline with agent type
pipeline = Pipeline(claude_api_key=config('CLAUDE_API_KEY'), agent_type="realestate")

# Store conversation state
conversation_id = None

# Configure audio options
options = AlgoOptions(
    audio_chunk_duration=0.4,
    started_talking_threshold=0.2,
    speech_threshold=0.3,
)

# Default messages
DEFAULT_STARTUP_MESSAGE = "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Welcome to MyHome Constructions. How may I help you with your real estate inquiries today?</prosody></speak>"
DEFAULT_ERROR_MESSAGE = "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I apologize, I couldn't understand. Please try again.</prosody></speak>"

# Startup function with error handling
def startup():
    global conversation_id
    pipeline.clear_history(conversation_id)
    try:
        for chunk in tts_model.generate_audio(text=DEFAULT_STARTUP_MESSAGE):
            yield chunk
    except Exception as e:
        yield b""

def process_audio(audio):
    global conversation_id
    
    try:
        # Process audio and get transcription and language
        transcript, detected_language = stt_model.process_audio(audio)

        if detected_language == 'unknown' or not transcript:
            try:
                return tts_model.generate_audio(text="<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I couldn't hear you clearly. Could you please repeat?</prosody></speak>")
            except Exception as e:
                return b""  # Return empty audio if TTS fails

        if detected_language != 'hindi' and detected_language != 'english' and detected_language != 'telugu':
            return tts_model.generate_audio(text="<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Kindly please repeat.</prosody></speak>")
        
        # Process through pipeline with consistent conversation_id
        if not conversation_id:
            conversation_id = str(uuid4())
        
        # Pass both transcript and detected language to pipeline
        result = pipeline.process(
            text=transcript,
            conversation_id=conversation_id,
            detected_language=detected_language
        )
        
        # Get response from pipeline
        response_text = result['response']
        
        # Generate and stream the response audio
        try:
            return tts_model.generate_audio(response_text)
        except Exception as e:
            # Fallback to a simple error message
            try:
                return tts_model.generate_audio(text=DEFAULT_ERROR_MESSAGE)
            except:
                return b""  # Return empty audio if even fallback TTS fails
    except Exception as e:
        return b""  # Return empty audio if TTS fails

# Create Stream with ReplyOnPause and concurrency settings
stream = Stream(
    handler=ReplyOnPause(process_audio, algo_options=options, startup_fn=startup),
    modality="audio",
    mode="send-receive"
    # max_connections=5  # Allow up to 5 concurrent connections
) 