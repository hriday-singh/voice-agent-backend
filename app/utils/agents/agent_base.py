from app.utils.speech_service import get_stt_model, get_tts_model
from app.utils.agent_config import get_agent_by_id, get_agent_error_messages
from app.utils.langgraph import get_agent_response
from decouple import config
from fastrtc import ReplyOnPause, AlgoOptions, Stream, SileroVadOptions
from uuid import uuid4
import numpy as np
import logging

class VoiceAgent:
    """Base class for voice agents using LangGraph for conversation management"""
    
    def __init__(self, agent_type):
        self.logger = logging.getLogger(__name__)
        
        # Agent configuration
        self.agent_type = agent_type
        self.agent_config = get_agent_by_id(agent_type)
        self.error_messages = get_agent_error_messages(agent_type)
        
        # Initialize models
        self.stt_model = get_stt_model()
        self.tts_model = get_tts_model()
        
        # Set agent type for STT model
        self.stt_model.set_agent_type(agent_type)
        
        # Set voice name if specified in config
        if self.agent_config and "voice_name" in self.agent_config:
            self.tts_model.set_voice_name(self.agent_config["voice_name"])
        
        # Store conversation state
        self.conversation_id = None
        
        # Default messages
        self.default_startup_message = self.agent_config.get(
            "startup_message", 
            f"<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Welcome to the {agent_type} service. How may I help you today?</prosody></speak>"
        )
        self.default_error_message = self.error_messages.get(
            "error", 
            "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I apologize, I couldn't understand. Please try again.</prosody></speak>"
        )
        
        # Configure audio options
        self.options = AlgoOptions(
            audio_chunk_duration=1.5,
            started_talking_threshold=0.4,
            speech_threshold=1.2,
        )
        
        self.rtc_configuration = {
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
        
        # Create stream with configured handler
        self.stream = Stream(
            handler=ReplyOnPause(
                self.process_audio, 
                algo_options=self.options, 
                model_options=SileroVadOptions(
                    threshold=0.95,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=1000,
                    speech_pad_ms=150
                ),
                startup_fn=self.startup,
                input_sample_rate=16000
            ),
            modality="audio",
            mode="send-receive",
            concurrency_limit=5,
            rtc_configuration=self.rtc_configuration
        )
    
    # Helper function for empty audio generator
    def empty_audio_iterator(self):
        yield (16000, np.zeros(1, dtype=np.float32))
    
    # Startup function with error handling
    def startup(self):
        self.conversation_id = None
        
        if self.agent_config.get("is_outbound"):
            try:
                for chunk in self.tts_model.generate_audio(text=self.default_startup_message):
                    yield chunk
            except Exception as e:
                self.logger.error(f"Error in startup: {e}")
                yield from self.empty_audio_iterator()
        else:
            return self.empty_audio_iterator()
    
    # Process audio function
    def process_audio(self, audio):
        try:
            # Process audio and get transcription
            transcript, detected_language = self.stt_model.process_audio(audio)
            
            if not transcript:
                return self.empty_audio_iterator()
                error_msg = self.error_messages.get(
                    "unclear_audio", 
                    "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I couldn't hear you clearly. Could you please repeat?</prosody></speak>"
                )
                try:
                    return self.tts_model.generate_audio(text=error_msg)
                except Exception as e:
                    self.logger.error(f"Error generating audio for unclear speech: {e}")
                    return self.empty_audio_iterator()
            
            # Create a unique conversation ID if needed
            if not self.conversation_id:
                self.conversation_id = str(uuid4())
            
            # Use LangGraph get_agent_response instead of Pipeline
            try:
                response_text = get_agent_response(
                    agent_id=self.agent_type,
                    user_input=transcript,
                    conversation_id=self.conversation_id
                )
            except Exception as e:
                self.logger.error(f"Error processing with LangGraph: {e}")
                return self.empty_audio_iterator()
            
            # Generate and stream the response audio
            try:
                return self.tts_model.generate_audio(response_text)
            except Exception as e:
                self.logger.error(f"Error generating audio response: {e}")
                try:
                    return self.tts_model.generate_audio(text=self.default_error_message)
                except Exception as e2:
                    self.logger.error(f"Error generating error audio: {e2}")
                    return self.empty_audio_iterator()
        except Exception as e:
            self.logger.error(f"Error in process_audio: {e}")
            return self.empty_audio_iterator() 