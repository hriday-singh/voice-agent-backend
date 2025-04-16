import requests
import base64
import numpy as np
import os
import re
from dotenv import load_dotenv
from typing import Generator, Tuple, Protocol, BinaryIO, Optional, Dict, Any, List
import io
import wave
from datetime import datetime
import pathlib
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from io import BytesIO
import pydub
from google.cloud import texttospeech
from google.cloud import speech
import logging
from app.utils.agent_config import get_agent_languages, get_agent_speech_context, get_voice_config, get_language_codes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class BaseSTT(Protocol):
    def transcribe(self, audio_file: BinaryIO, agent_type: Optional[str] = None) -> tuple[str, str]:
        """Convert audio file to text
        Returns:
            tuple: (transcript, detected_language)
        """
        ...

class BaseTTS(Protocol):
    """Base protocol for text-to-speech providers"""
    def set_language(self, lang: str) -> None:
        """Set the language for TTS"""
        ...

    def synthesize(self, text: str) -> bytes:
        """Convert text to audio data"""
        ...

class STTProvider(Protocol):
    """Protocol for speech-to-text providers"""
    def process_audio(self, audio_frame: Tuple[int, np.ndarray] | np.ndarray) -> str:
        """Process audio frame and return transcript"""
        ...
        
class TTSProvider(Protocol):
    """Protocol for text-to-speech providers"""
    def set_language(self, lang: str) -> None:
        """Set the language for TTS"""
        ...

    def generate_audio(self, text: str) -> Generator[Tuple[int, np.ndarray], None, None]:
        """Generate audio chunks from text"""
        ...

class AudioProcessor:
    def __init__(self):
        self.sample_rate = 16000  # Default STT sample rate
        self.tts_sample_rate = 24000  # Default TTS sample rate
        
        # Create directory for saving audio files
        self.audio_dir = pathlib.Path("audio_recordings")
        self.audio_dir.mkdir(exist_ok=True)

    def numpy_to_wav(self, audio_data: np.ndarray, sample_rate: int = None) -> bytes:
        """Convert numpy array to WAV format"""
        if sample_rate is None:
            sample_rate = self.sample_rate
            
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)  # mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.astype(np.int16).tobytes())
            return wav_io.getvalue()

    def wav_to_numpy(self, wav_data: bytes) -> Tuple[int, np.ndarray]:
        """Convert WAV data to numpy array with sample rate"""
        with io.BytesIO(wav_data) as wav_io:
            with wave.open(wav_io, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                audio_data = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype=np.int16)
                return sample_rate, audio_data.astype(np.float32) / 32768.0  # Normalize to [-1, 1]

    def save_audio(self, audio_data: bytes) -> str:
        """Save audio file with timestamp and return the path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = self.audio_dir / f"tts_output_{timestamp}.wav"
        with open(audio_path, "wb") as f:
            f.write(audio_data)
            logger.info(f"Saved audio to {audio_path}")
        return str(audio_path)

class MP3AudioProcessor:
    """Audio processor specifically for MP3 data from ElevenLabs"""
    def __init__(self):
        self.sample_rate = 22050  # ElevenLabs default sample rate
        
        # Create directory for saving audio files
        self.audio_dir = pathlib.Path("audio_recordings")
        self.audio_dir.mkdir(exist_ok=True)
    
    def mp3_to_numpy(self, mp3_data: bytes) -> Tuple[int, np.ndarray]:
        """Convert MP3 data to numpy array
        Args:
            mp3_data: Raw MP3 data in bytes
        Returns:
            tuple: (sample_rate, audio_array)
        """
        # Load MP3 data using pydub
        audio = pydub.AudioSegment.from_mp3(BytesIO(mp3_data))
        
        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        
        # Normalize to [-1, 1]
        samples = samples / (1 << (8 * audio.sample_width - 1))
        
        return audio.frame_rate, samples

    def save_audio(self, audio_data: bytes) -> str:
        """Save audio file with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = self.audio_dir / f"tts_output_{timestamp}.mp3"
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        return str(audio_path)

class STTWrapper:
    """Wrapper for STT providers that adapts them to our protocol"""
    def __init__(self, provider: BaseSTT):
        self.provider = provider
        self.audio_processor = AudioProcessor()
        self.current_agent_type = None
        
    def set_agent_type(self, agent_type: str) -> None:
        """Set the agent type for language configuration
        
        Args:
            agent_type: Type of agent to use (e.g., 'realestate', 'hospital')
        """
        self.current_agent_type = agent_type
        
    def process_audio(self, audio_frame: Tuple[int, np.ndarray] | np.ndarray) -> str:
        """Process audio frame and return transcript"""
        # Extract audio data
        if isinstance(audio_frame, tuple):
            sample_rate, audio_data = audio_frame
        else:
            sample_rate = self.audio_processor.sample_rate
            audio_data = audio_frame
            
        # Convert to WAV format - only do this conversion once
        wav_data = self.audio_processor.numpy_to_wav(audio_data, sample_rate)
        
        # Create file-like object
        audio_file = io.BytesIO(wav_data)

        # Save the audio file
        # self.audio_processor.save_audio(wav_data)
        
        # Transcribe with agent type if available
        transcript = self.provider.transcribe(audio_file, self.current_agent_type)
        
        return transcript

class TTSWrapper:
    """Wrapper around TTS implementations to standardize output format"""
    
    def __init__(self, provider: BaseTTS):
        """Create a new TTS wrapper
        Args:
            provider: TTS implementation
        """
        self.provider = provider
        
        # Check if the provider has MP3 output (ElevenLabs)
        if isinstance(provider, ElevenLabsTTS):
            self.audio_proc = MP3AudioProcessor()
        else:
            self.audio_proc = AudioProcessor()
            
        # Set the default chunk size for streaming audio
        self.chunk_size = 4096

    def set_language(self, lang: str) -> None:
        """Set the language for TTS
        Args:
            lang: Language code (BCP-47 format, e.g., 'en-IN', 'hi-IN')
        """
        self.provider.set_language(lang)

    def generate_audio(self, text: str) -> Generator[Tuple[int, np.ndarray], None, None]:
        # Get audio data from TTS
        audio_data = self.provider.synthesize(text)
        if not audio_data:
            yield (self.audio_proc.sample_rate, np.array([], dtype=np.float32))
            return

        # Save the generated audio file
        # self.audio_proc.save_audio(audio_data) # Commented out to make it faster
            
        # Convert to numpy array and stream in chunks
        if isinstance(self.provider, ElevenLabsTTS):
            sample_rate, audio_array = self.audio_proc.mp3_to_numpy(audio_data)
        else:
            sample_rate, audio_array = self.audio_proc.wav_to_numpy(audio_data)
        
        # Stream in chunks for more efficient processing
        for i in range(0, len(audio_array), self.chunk_size):
            yield (sample_rate, audio_array[i:i + self.chunk_size])

class ElevenLabsTTS:
    """TTS provider using ElevenLabs API"""
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
            
        # Initialize the client
        try:
            from elevenlabs import set_api_key, voices
            set_api_key(self.api_key)
            available_voices = voices()
            if not available_voices:
                raise ValueError("No voices found in ElevenLabs account")
        except Exception as e:
            logger.error(f"Error initializing ElevenLabs: {str(e)}")
            raise
            
        # Initialize with English as default
        self.current_language = 'english'
        self.voice_config = {
            'hindi': {
                'voice_id': 'wlmwDR77ptH6bKHZui0l',  # Hindi multilingual voice
                'speed': 1.0,
                'language': 'hi',
                'model_id': 'eleven_turbo_v2_5'
            },
            'english': {
                'voice_id': '90ipbRoKi4CpHXvKVtl0',  # English voice
                'speed': 1.0,
                'language': 'en',
                'model_id': 'eleven_flash_v2_5'
            },
            'tamil': {
                'voice_id': '1XNFRxE3WBB7iI0jnm7p',  # Using the same multilingual voice for Tamil
                'speed': 1.0,
                'language': 'ta',
                'model_id': 'eleven_flash_v2_5'  # Using turbo model for better multilingual support
            }
        }
    
    def set_language(self, language_code: str) -> None:
        """Set the language for TTS
        Args:
            language_code: BCP-47 language code (e.g., 'en-IN', 'hi-IN')
        """
        if language_code in self.language_code_map:
            self.current_language_code = language_code
        else:
            # Default to English if language code not found
            logger.warning(f"Language code {language_code} not found in ElevenLabs configuration, defaulting to en-IN")
            self.current_language_code = 'en-IN'
    
    def synthesize(self, text: str) -> bytes:
        """Convert text to audio using ElevenLabs API
        Args:
            text: Text to convert to speech
        Returns:
            bytes: Audio data in bytes
        """
        try:
            if not text.strip():  # Check if text is empty or whitespace
                return b""
            
            # Special handling for Yashoda pronunciation in English
            if self.current_language_code.startswith('en-'):
                # Direct text substitution without SSML tags - use phonetic spelling
                text = re.sub(r'\bYashoda\b', 'ya-show-dha', text, flags=re.IGNORECASE)
                text = re.sub(r'\bYASHODA\b', 'ya-show-dha', text)
                text = re.sub(r'\bYashodha\b', 'ya-show-dha', text, flags=re.IGNORECASE)
            
            # Get voice configuration for current language
            voice_config = self.language_code_map.get(self.current_language_code, self.language_code_map['en-IN'])
            
            # Configure voice settings
            voice_settings = VoiceSettings(
                stability=0.75,         # Increased for a more consistent, controlled tone
                similarity_boost=0.75,  # A bit higher to enhance clarity and preserve the speaker's identity
                style=0.2,             # Adds a subtle professional warmth without compromising neutrality
                use_speaker_boost=True,  # Retains speaker boosting for clearer enunciation
                speed=voice_config['speed']
            )
            
            # Get streaming response from ElevenLabs API
            response = self.client.text_to_speech.convert(
                voice_id=voice_config['voice_id'],
                output_format="mp3_22050_32",
                text=text,
                model_id=voice_config['model_id'],
                voice_settings=voice_settings
            )
            
            # Create a BytesIO object to hold the audio data
            audio_stream = BytesIO()
            
            # Write each chunk of audio data to the stream
            for chunk in response:
                if chunk:
                    audio_stream.write(chunk)
            
            # Get the final bytes
            audio_stream.seek(0)
            return audio_stream.read()
            
        except Exception as e:
            logger.error(f"Error in ElevenLabsTTS synthesize: {str(e)}")
            return b""

class GoogleTTS:
    """TTS provider using Google Cloud Text-to-Speech API"""
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        try:
            # Try API key authentication first
            if self.api_key:
                from google.cloud import texttospeech_v1
                from google.api_core import client_options
                
                # Create client with API key
                options = client_options.ClientOptions(
                    api_key=self.api_key
                )
                self.client = texttospeech_v1.TextToSpeechClient(client_options=options)
            
            # Fall back to service account credentials if API key not found
            elif self.credentials_path:
                import google.cloud.texttospeech as tts
                self.client = tts.TextToSpeechClient()
            else:
                raise ValueError(
                    "Neither GOOGLE_API_KEY nor GOOGLE_APPLICATION_CREDENTIALS environment variables are set. "
                    "Please set either:\n"
                    "1. GOOGLE_API_KEY with your API key, or\n"
                    "2. GOOGLE_APPLICATION_CREDENTIALS with path to your service account JSON file"
                )
        
        except Exception as e:
            logger.error(f"Error initializing Google TTS client: {str(e)}")
            raise
        
        # Initialize with English as default
        self.current_language_code = 'en-IN'
        
        # Get voice configurations from database using our helper function
        self.voice_config_db = get_voice_config()
        
        # Create language code to configuration mapping
        self.language_code_map = {}
        for lang_name, config in self.voice_config_db.items():
            if isinstance(config, dict) and 'language_code' in config:
                self.language_code_map[config['language_code']] = {
                    'language_code': config['language_code'],
                    'voice_name': config.get('voice_name')
                }       
        
        # Audio configuration optimized for telephony
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            effects_profile_id=['handset-class-device'],
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=2.0
        )
    
    def set_language(self, language_code: str) -> None:
        """Set the language for TTS using language code
        Args:
            language_code: BCP-47 language code (e.g., 'en-IN', 'hi-IN')
        """
        if language_code in self.language_code_map:
            self.current_language_code = language_code
        else:
            # Default to English if language code not found
            logger.warning(f"Language code {language_code} not found in configuration, defaulting to en-IN")
            self.current_language_code = 'en-IN'
    
    def synthesize(self, ssml_text: str) -> bytes:
        """Convert text to audio using Google Cloud TTS
        Args:
            text: Text to convert to speech
        Returns:
            bytes: WAV audio data
        """
        try:
            if not ssml_text.strip():  # Check if text is empty or whitespace
                return b""            
            
            # Get voice configuration for current language code
            voice_config = self.language_code_map.get(self.current_language_code, self.language_code_map.get('en-IN'))
            
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=voice_config['language_code'],
                name=voice_config['voice_name'],  # Use voice name from configuration
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE # Hardcoded to female voice
            )

            try:
                # Perform the text-to-speech request
                response = self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=self.audio_config
                )
                return response.audio_content
                
            except Exception as api_error:
                logger.error(f"API Error in GoogleTTS synthesize: {str(api_error)}")
                # If authentication fails, try to refresh credentials
                if "authentication" in str(api_error).lower():
                    logger.info("Attempting to refresh credentials...")
                    self.__init__()  # Reinitialize client
                    response = self.client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice,
                        audio_config=self.audio_config
                    )
                    return response.audio_content
                raise
            
        except Exception as e:
            logger.error(f"Error in GoogleTTS synthesize: {str(e)}")
            return b""

class SarvamSTT:
    def __init__(self):
        self.api_key = os.getenv('SARVAM_API_KEY')
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable not set")
            
        self.stt_url = 'https://api.sarvam.ai/speech-to-text'
        
        # Map our language format to Sarvam BCP-47 codes
        self.language_map = {
            'telugu': 'te-IN',
            'hindi': 'hi-IN',
            'english': 'en-IN'
        }
        
        # Reverse mapping for response handling
        self.reverse_language_map = {v: k for k, v in self.language_map.items()}

    def transcribe(self, audio_file: BinaryIO) -> tuple[str, str]:
        """Convert audio file to text using Sarvam API
        Returns:
            tuple: (transcript, detected_language)
        """
        try:
            headers = {
                'api-subscription-key': self.api_key
            }
            
            files = {
                'file': ('audio.wav', audio_file, 'audio/wav'),
                'model': (None, 'saarika:v2'),  # Using v2 model for better accuracy
                'language_code': (None, 'unknown'),  # Let API detect language
                'with_timestamps': (None, 'false'),
                'with_diarization': (None, 'false')
            }
            
            response = requests.post(self.stt_url, files=files, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Sarvam API Error: {response.text}")
            
            response_json = response.json()
            transcript = response_json.get('transcript', '')
            
            # Get language code from response and map to our format
            detected_language = response_json.get('language_code')
            if detected_language:
                # Default to english for any unknown language code
                detected_language = self.reverse_language_map.get(detected_language, 'telugu')
            else:
                detected_language = 'unknown'
            
            return transcript, detected_language
            
        except Exception as e:
            logger.error(f"Error in SarvamSTT transcribe: {str(e)}")
            return "", "unknown"

    def set_language(self, lang: str):
        """Set the current language for TTS"""
        language_map = {
            'hindi': 'hi',
            'english': 'en',
            'tamil': 'ta',
            'telugu': 'te'
        }
        
        mapped_lang = language_map.get(lang, lang)
        if mapped_lang in self.voice_config:
            self.current_language = mapped_lang

    def synthesize(self, text: str) -> bytes:
        """Convert text to audio using Sarvam API"""
        try:
            if not text.strip():  # Check if text is empty or whitespace
                return b""

            voice_settings = self.voice_config[self.current_language]
            
            headers = {
                'Content-Type': 'application/json',
                'api-subscription-key': self.api_key
            }
            
            data = {
                'inputs': [text],  # List of strings, each <= 500 chars
                'target_language_code': voice_settings['language'],
                'speaker': voice_settings['voice_id'],
                'pitch': 0,  # Range: -1 to 1
                'pace': min(max(voice_settings['speed'], 0.3), 3.0),  # Clamp to valid range
                'loudness': 1.2,  # Range: 0 to 3
                'speech_sample_rate': 22050,  # One of: 8000, 16000, 22050
                'enable_preprocessing': True,  # For better handling of mixed-language text
                'model': 'bulbul:v1'  # Currently only available model
            }
            
            response = requests.post(self.tts_url, headers=headers, json=data)
            
            if response.status_code != 200:
                raise Exception(f"Sarvam API Error: {response.text}")
            
            # Return raw base64 decoded audio
            audio_base64 = response.json()['audios'][0]
            return base64.b64decode(audio_base64)
            
        except Exception as e:
            logger.error(f"Error in SarvamTTS synthesize: {str(e)}")
            return b""

class GoogleSTT:
    """STT provider using Google Cloud Speech-to-Text API"""
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # Cache for agent settings to avoid repeated DB calls
        self._agent_settings_cache = {}
        
        try:
            # Try API key authentication first
            if self.api_key:
                from google.cloud import speech_v1
                from google.api_core import client_options
                
                # Create client with API key
                options = client_options.ClientOptions(
                    api_key=self.api_key
                )
                self.client = speech_v1.SpeechClient(client_options=options)
            
            # Fall back to service account credentials if API key not found
            elif self.credentials_path:
                self.client = speech.SpeechClient()
            else:
                raise ValueError(
                    "Neither GOOGLE_API_KEY nor GOOGLE_APPLICATION_CREDENTIALS environment variables are set. "
                    "Please set either:\n"
                    "1. GOOGLE_API_KEY with your API key, or\n"
                    "2. GOOGLE_APPLICATION_CREDENTIALS with path to your service account JSON file"
                )
            
            # Map our language format to Google BCP-47 codes
            self.language_map = get_language_codes()
            
            # Reverse mapping for detection
            self.reverse_language_map = {v: k for k, v in self.language_map.items()}
            
        except Exception as e:
            logger.error(f"Error initializing Google STT client: {str(e)}")
            raise

    def _get_agent_settings(self, agent_type: str) -> tuple:
        """Get agent settings with caching to avoid repeated DB calls
        
        Returns:
            tuple: (primary_language_code, alternative_language_codes, speech_context_phrases)
        """
        # Return from cache if available
        if agent_type in self._agent_settings_cache:
            return self._agent_settings_cache[agent_type]
            
        # Default settings
        primary_language_code = 'en-IN'
        alternative_language_codes = ['hi-IN', 'en-IN', 'te-IN']
        speech_context_phrases = []
            
        # Get agent-specific settings
        if agent_type:
            agent_languages = get_agent_languages(agent_type)
            if agent_languages:
                # Get primary language
                primary_language_code = agent_languages.get("primary", 'en-IN')
                
                # Get supported languages excluding primary
                supported_languages = agent_languages.get("supported", [])
                alternative_language_codes = [lang for lang in supported_languages if lang != primary_language_code]
                
            # Get agent-specific speech context phrases
            speech_context_phrases = get_agent_speech_context(agent_type)
            
        # Cache the settings
        self._agent_settings_cache[agent_type] = (primary_language_code, alternative_language_codes, speech_context_phrases)
        return self._agent_settings_cache[agent_type]

    def transcribe(self, audio_file: BinaryIO, agent_type: Optional[str] = None) -> tuple[str, str]:
        """Convert audio file to text using Google Cloud Speech-to-Text API
        Args:
            audio_file: Audio file in WAV format
            agent_type: Type of agent being used (optional, for language selection)
        Returns:
            tuple: (transcript, detected_language)
        """
        try:
            # Read the audio data
            audio_content = audio_file.read()
            
            # Create the recognition audio object
            audio = speech.RecognitionAudio(content=audio_content)
            
            # Get agent settings (using cached values)
            primary_language_code, alternative_language_codes, speech_context_phrases = self._get_agent_settings(agent_type) if agent_type else ('en-IN', ['hi-IN', 'en-IN', 'te-IN'], [])
            
            # Configure speech contexts with agent-specific phrases if available
            speech_contexts = []
            if speech_context_phrases:
                speech_contexts = [
                    speech.SpeechContext(
                        phrases=speech_context_phrases,
                        boost=7  # Adjust boost as needed
                    )
                ]
            
            # Configure the recognition settings
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                enable_automatic_punctuation=True,
                model='default',  # Can be 'video', 'phone_call', 'command_and_search', etc.
                language_code=primary_language_code,  # Use agent's primary language
                alternative_language_codes=alternative_language_codes,  # Use agent's supported languages
                enable_spoken_emojis=False,
                use_enhanced=True,
                audio_channel_count=1
                # speech_contexts=speech_contexts
            )
            # Perform the transcription
            response = self.client.recognize(config=config, audio=audio)

            # logger.info("response",response)
            
            if not response.results:
                logger.error("No results from Google STT")
                return "", "unknown"
            
            # Get the transcript from the first result
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            
            logger.info(f"Transcribed text: '{transcript}', confidence: {confidence}")
            return transcript
            
        except Exception as e:
            logger.error(f"Error in GoogleSTT transcribe: {str(e)}")
            return "", "unknown"

class ElevenLabsSTT:
    """STT provider using ElevenLabs API"""
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        
        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=self.api_key)
        
        # Map our language format to ElevenLabs language codes
        self.language_map = {
            'hindi': 'hin',  # Updated to match ElevenLabs expected codes
            'english': 'eng'  # Updated to match ElevenLabs expected codes
        }
        
        # Reverse mapping for response handling
        self.reverse_language_map = {v: k for k, v in self.language_map.items()}

    def transcribe(self, audio_file: BinaryIO) -> tuple[str, str]:
        """Convert audio file to text using ElevenLabs API
        Args:
            audio_file: Audio file in WAV format
        Returns:
            tuple: (transcript, detected_language)
        """
        try:
            # Read the audio data
            audio_content = audio_file.read()
            
            # Reset file pointer to beginning (some APIs need this)
            audio_file.seek(0)
            
            # Create a BytesIO object with the audio content
            audio_bytes = BytesIO(audio_content)
            
            # Call ElevenLabs API for transcription with parameters according to documentation
            transcription = self.client.speech_to_text.convert(
                file=audio_bytes,
                model_id="scribe_v1",  # Current model for transcription
                # tag_audio_events=True,  # Tag audio events like laughter, applause, etc.
                # language_code=None,     # None for automatic language detection
                diarize=False           # Don't annotate who is speaking
            )
            
            if not hasattr(transcription, 'text') or not transcription.text:
                return "", self.default_language
            
            # Get the transcript from the response
            transcript = transcription.text
            
            # Get the detected language
            detected_language_code = transcription.language_code
            
            if detected_language_code:
                # Map the 3-letter code to our language format (hindi/english)
                if detected_language_code == 'hin':
                    detected_language = 'hindi'
                elif detected_language_code == 'eng':
                    detected_language = 'english'
            
            return transcript, detected_language
            
        except Exception as e:
            logger.error(f"Error in ElevenLabsSTT transcribe: {str(e)}")
            return "", "english"

def get_stt_model() -> STTProvider:
    """Get STT model"""
    # Uncomment the provider you want to use
    return STTWrapper(GoogleSTT())

def get_tts_model() -> TTSProvider:
    """Get TTS model"""
    # Uncomment the provider you want to use
    return TTSWrapper(GoogleTTS())