from app.utils.speech_service import get_stt_model, get_tts_model
from app.utils.pipeline import Pipeline
from app.utils.agent_config import get_agent_by_id
from decouple import config
from fastrtc import ReplyOnPause, AlgoOptions, Stream
from uuid import uuid4
import numpy as np


# Get agent configuration
agent_config = get_agent_by_id("hospital")

# Initialize models
stt_model = get_stt_model()
tts_model = get_tts_model()

# Set agent type for STT model
stt_model.set_agent_type("hospital")

pipeline = Pipeline(anthropic_api_key=config('CLAUDE_API_KEY'), agent_type="hospital")

# Set voice name if specified in config
if agent_config and "voice_name" in agent_config:
    tts_model.set_voice_name(agent_config["voice_name"])

# Store conversation state
conversation_id = None

# Configure audio options
options = AlgoOptions(
    audio_chunk_duration=agent_config.get("audio_chunk_duration", 0.8),
    started_talking_threshold=agent_config.get("started_talking_threshold", 0.4),
    speech_threshold=agent_config.get("speech_threshold", 0.7),
)

rtc_configuration = {
    "iceServers": [
        {
            "urls": [
                "stun:40.192.23.46:3478",
                "turn:40.192.23.46:3478"
            ],
            "username": "cawturnserver",
            "credential": "servercawturn"
        }
    ]
}

# Default messages from agent_configs.json
DEFAULT_STARTUP_MESSAGE = agent_config.get("startup_message", "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Welcome to <speak><phoneme alphabet='ipa' ph='jəˈʃoːda'>Yashoda</phoneme></speak> Hospital. How may I assist you with your appointment or medical inquiry today?</prosody></speak>")
DEFAULT_ERROR_MESSAGE = agent_config.get("error_messages", {}).get("error", "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I apologize, I couldn't understand. Please try again.</prosody></speak>")

# Helper function for empty audio generator
def empty_audio_iterator():
    # Create a generator that yields a single empty/silent frame
    # Use a valid sample rate (16000) instead of 0 to prevent ZeroDivisionError in librosa.resample
    yield (16000, np.zeros(1, dtype=np.float32))

# Startup function with error handling
def startup():
    global conversation_id
    pipeline.clear_history(conversation_id)
    try:
        for chunk in tts_model.generate_audio(text=DEFAULT_STARTUP_MESSAGE):
            yield chunk
    except Exception as e:
        yield from empty_audio_iterator()

def process_audio(audio):
    global conversation_id
    
    try:
        # Process audio and get transcription and language
        transcript, detected_language = stt_model.process_audio(audio)

        if not transcript:
            # Get error message from agent config
            error_msg = agent_config.get("error_messages", {}).get("unclear_audio", 
                     "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I couldn't hear you clearly. Could you please repeat?</prosody></speak>")
            try:
                return tts_model.generate_audio(text=error_msg)
            except Exception as e:
                return empty_audio_iterator()
        
        # Process through pipeline with consistent conversation_id
        if not conversation_id:
            conversation_id = str(uuid4())
        
        # Pass transcript to pipeline (language detection is now handled in the STT module)
        try:
            result = pipeline.process(
                text=transcript,
                conversation_id=conversation_id,
                detected_language=detected_language
            )
        except Exception as e:
            return empty_audio_iterator()
        
        # Get response from pipeline
        response_text = result['response']
        # Generate and stream the response audio
        try:
            return tts_model.generate_audio(response_text)
        except Exception as e:
            try:
                return tts_model.generate_audio(text=DEFAULT_ERROR_MESSAGE)
            except:
                return empty_audio_iterator()
    except Exception as e:
        try:
            return tts_model.generate_audio(text=DEFAULT_ERROR_MESSAGE)
        except:
            return empty_audio_iterator()

# Create Stream with ReplyOnPause
stream = Stream(
    handler=ReplyOnPause(process_audio, algo_options=options, startup_fn=startup),
    modality="audio",
    mode="send-receive",
    concurrency_limit=20,
    rtc_configuration=rtc_configuration
) 