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
from app.utils.agent_config import get_agent_languages, get_agent_speech_context
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global pronunciation dictionary for common terms
# This can be imported and used throughout the application
PRONUNCIATION_DICTIONARY = {
    # Hospital names
    "Yashodha": {
        "pronunciation": "jəˈʃoːd̪ʰaː",
        "alphabet": "ipa"
    },
    "Yashoda": {
        "pronunciation": "jəˈʃoːd̪ʰaː",
        "alphabet": "ipa"
    },
    "YASHODA": {
        "pronunciation": "jəˈʃoːd̪ʰaː",
        "alphabet": "ipa"
    },
    "yashodha": {
        "pronunciation": "jəˈʃoːd̪ʰaː",
        "alphabet": "ipa"
    },
    "yashoda": {
        "pronunciation": "jəˈʃoːd̪ʰaː",
        "alphabet": "ipa"
    },
    
    # Medical terms
    "pneumonia": {
        "pronunciation": "nuːˈmoʊniə",
        "alphabet": "ipa"
    },
    "myocardial infarction": {
        "pronunciation": "maɪəˈkɑɹdiəl ɪnˈfɑɹkʃən",
        "alphabet": "ipa"
    },
    "fever": {
        "pronunciation": "ˈfiːvər",
        "alphabet": "ipa"
    },
    "headache": {
        "pronunciation": "ˈhɛdeɪk",
        "alphabet": "ipa"
    },
    
    # Place names
    "Chennai": {
        "pronunciation": "ˈtʃɛnaj",
        "alphabet": "ipa"
    },
    "Delhi": {
        "pronunciation": "ˈd̪ɛli",
        "alphabet": "ipa"
    },
    
    # Language names
    "Tamil": {
        "pronunciation": "ˈt̪ɑːmɪl",
        "alphabet": "ipa"
    },
    "Tamil Nadu": {
        "pronunciation": "ˈt̪ɑːmɪl ˈnɑːɖu",
        "alphabet": "ipa"
    },
    "Hindi": {
        "pronunciation": "ˈhɪndi",
        "alphabet": "ipa"
    },
    
    # Technical terms
    "SQL": {
        "pronunciation": "ˈɛs kjuː ˈɛl",
        "alphabet": "ipa"
    },
    "GUID": {
        "pronunciation": "ˈɡuːɪd",
        "alphabet": "ipa"
    },
    "PostgreSQL": {
        "pronunciation": "ˈpoʊstɡrɛs ˈɛs kjuː ˈɛl",
        "alphabet": "ipa"
    }
}

# Tamil dictionary
TAMIL_PRONUNCIATIONS = {
    "காய்ச்சல்": {
        "pronunciation": "kaːjtːʃal",
        "alphabet": "ipa"
    },
    "தலைவலி": {
        "pronunciation": "t̪alaɪvali",
        "alphabet": "ipa"
    },
    "மருத்துவமனைக்கு": {
        "pronunciation": "maɾuθθuvamaneːkku",
        "alphabet": "ipa"
    },
    "யசோதா": {  # Yashodha in Tamil
        "pronunciation": "jəˈʃoːd̪ʰaː",
        "alphabet": "ipa"
    }
}

# Hindi dictionary
HINDI_PRONUNCIATIONS = {
    "बुखार": {
        "pronunciation": "buˈkʰaːr",
        "alphabet": "ipa"
    },
    "सिरदर्द": {
        "pronunciation": "sirˈdərd",
        "alphabet": "ipa"
    },
    "यशोधा": {  # Yashodha in Hindi
        "pronunciation": "jəˈʃoːd̪ʰaː",
        "alphabet": "ipa"
    }
}

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
        
    def set_voice_name(self, voice_name: str) -> None:
        """Set specific voice name (optional)"""
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
        
    def set_voice_name(self, voice_name: str) -> None:
        """Set specific voice name"""
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
        # Convert to WAV format
        wav_data = self.audio_processor.numpy_to_wav(audio_data, sample_rate)
        
        # Create file-like object
        audio_file = io.BytesIO(wav_data)
        
        # Transcribe with agent type if available
        transcript, detected_language = self.provider.transcribe(audio_file, self.current_agent_type)
        
        return transcript, detected_language

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

    def set_language(self, lang: str) -> None:
        self.provider.set_language(lang)
        
    def set_voice_name(self, voice_name: str) -> None:
        """Set a specific voice name if provider supports it"""
        if hasattr(self.provider, 'set_voice_name'):
            self.provider.set_voice_name(voice_name)

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
        
        chunk_size = 4096
        for i in range(0, len(audio_array), chunk_size):
            yield (sample_rate, audio_array[i:i + chunk_size])

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
    
    def set_language(self, lang: str) -> None:
        """Set the language for TTS
        Args:
            lang: Language code ('hindi', 'english', or 'tamil')
        """
        if lang in self.voice_config:
            self.current_language = lang
    
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
            if self.current_language == 'english':
                # Direct text substitution without SSML tags - use phonetic spelling
                text = re.sub(r'\bYashoda\b', 'ya-show-dha', text, flags=re.IGNORECASE)
                text = re.sub(r'\bYASHODA\b', 'ya-show-dha', text)
                text = re.sub(r'\bYashodha\b', 'ya-show-dha', text, flags=re.IGNORECASE)
            
            # Get voice configuration for current language
            voice_config = self.voice_config.get(self.current_language, self.voice_config['english'])
            
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

class GoogleTTS_SSML:
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
        self.current_language = 'english'
        
        # Voice configurations for different languages
        self.voice_config = {
            'hindi': {
                'language_code': 'hi-IN',
                'name': 'hi-IN-Wavenet-E',  # Female voice
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            },
            'english': {
                'language_code': 'en-IN',
                'name': 'en-IN-Wavenet-E',  # Female voice
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            },
            'tamil': {
                'language_code': 'ta-IN',
                'name': 'ta-IN-Wavenet-A',  # Female voice
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            },
            'telugu': {
                'language_code': 'te-IN',
                'name': 'te-IN-Standard-A',  # Female voice
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            }
        }
        
        # Audio configuration optimized for telephony
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            effects_profile_id=['handset-class-device'],
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=2.0
        )

    def detect_emotion(self, sentence):
        """Detects the emotion/tone of a sentence based on content analysis.
        Returns one of: "urgent", "empathetic", "informative", "greeting", "professional"
        """
        # Define keyword lists for hospital context in multiple languages
        urgent_keywords = [
            # English
            "emergency", "critical", "urgent", "severe", "immediately", "call 108", "ambulance",
            "chest pain", "breathing difficulty", "unconscious", "bleeding", "accident",
            # Hindi
            "आपातकालीन", "तत्काल", "आपात", "आपातकाल", "छाती में दर्द", "सांस लेने में तकलीफ",
            # Tamil
            "அவசர", "மார்பு வலி", "மூச்சுத்திணறல்",
            # Telugu
            "అత్యవసర", "తీవ్రమైన", "తక్షణ", "గుండె నొప్పి", "శ్వాస తీసుకోవడంలో ఇబ్బంది"
        ]
        
        empathetic_keywords = [
            # English 
            "pain", "suffering", "worried", "concerned", "anxious", "afraid", "scared",
            "baby", "child", "pregnant", "family",
            # Hindi
            "दर्द", "परेशान", "चिंतित", "बच्चा", "शिशु", "गर्भवती", "परिवार",
            # Tamil
            "வலி", "கவலை", "குழந்தை", "குடும்பம்", "கர்ப்பிணி",
            # Telugu
            "నొప్పి", "బాధ", "ఆందోళన", "చింతిత", "బిడ్డ", "గర్భిణీ", "కుటుంబం"
        ]
        
        informative_keywords = [
            # English
            "appointment", "schedule", "doctor", "available", "location", "directions", "fee",
            "timing", "consultation", "procedure", "test", "results", "registration",
            # Hindi
            "अपॉइंटमेंट", "डॉक्टर", "उपलब्ध", "स्थान", "शुल्क", "समय", "परामर्श", "प्रक्रिया", "परीक्षण",
            # Tamil
            "பதிவு", "மருத்துவர்", "இடம்", "கட்டணம்", "நேரம்",
            # Telugu
            "అపాయింట్మెంట్", "డాక్టర్", "అందుబాటులో", "ప్రదేశం", "రుసుము", "సమయం", "సంప్రదింపు", "పరీక్ష"
        ]
        
        greeting_keywords = [
            # English
            "hello", "hi", "greetings", "welcome", "good morning", "good afternoon", 
            # Hindi
            "नमस्ते", "नमस्कार", "स्वागत", "शुभ",
            # Tamil
            "வணக்கம்", "நல்வரவு",
            # Telugu
            "నమస్కారం", "హలో", "స్వాగతం", "శుభోదయం"
        ]
        
        sentence_lower = sentence.lower()
        
        # Check for urgent situations first (highest priority)
        for word in urgent_keywords:
            if word.lower() in sentence_lower:
                return "urgent"
        
        # Check for situations requiring empathy
        for word in empathetic_keywords:
            if word.lower() in sentence_lower:
                return "empathetic"
        
        # Check for informational content
        for word in informative_keywords:
            if word.lower() in sentence_lower:
                return "informative"
        
        # Check for greetings
        for word in greeting_keywords:
            if word.lower() in sentence_lower:
                return "greeting"
        
        # Default tone is professional
        return "professional"

    def interpret_numbers(self, sentence):
        """Enhances numeric sequences with SSML say-as tags for medical context"""
        # Fix Rs. currency handling before main processing
        sentence = re.sub(r'Rs\.\s*(\d+)', r'rupees \1', sentence)
        sentence = re.sub(r'Rs\s*(\d+)', r'rupees \1', sentence)
        sentence = re.sub(r'INR\s*(\d+)', r'rupees \1', sentence)
        sentence = re.sub(r'₹\s*(\d+)', r'rupees \1', sentence)
        
        # Fix Dr. spacing issue 
        sentence = re.sub(r'Dr\.\s+', r'Doctor ', sentence)
        
        # Process different number formats
        def repl(match):
            number = match.group(0)
            
            # Phone numbers
            if len(number) == 10 and number.isdigit():
                return f'<say-as interpret-as="telephone">{number}</say-as>'
            
            # Emergency numbers (like 108)
            elif len(number) <= 3 and number.isdigit():
                return f'<say-as interpret-as="cardinal">{number}</say-as>'
            
            # Dates (simple pattern match)
            elif re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', number):
                parts = number.split('/')
                if len(parts) == 3:
                    day, month, year = parts
                    # Format for better pronunciation
                    if len(year) == 2:
                        year = '20' + year
                    return f'<say-as interpret-as="date" format="dmy">{day}/{month}/{year}</say-as>'
                # <say-as interpret-as="date" format="dmy">01/02/1960</say-as>
                return f'<say-as interpret-as="date" format="dmy">{number}</say-as>'
            
            # Time (HH:MM format)
            elif re.match(r'\d{1,2}:\d{2}', number):
                hour, minute = number.split(':')
                if int(minute) == 0:
                    return f'{hour} o\'clock'
                elif int(minute) == 30:
                    return f'{hour} thirty'
                else:
                    return f'<say-as interpret-as="time" format="hms24">{hour}:{minute}</say-as>'
            
            # AM/PM time handling
            elif re.search(r'\d{1,2}:\d{2}\s*(AM|PM|am|pm)', sentence):
                if re.match(r'\d{1,2}:\d{2}\s*(AM|PM|am|pm)', number):
                    time_part, period = number.split(':')
                    hour = time_part
                    if ':' in period:
                        min_period = period.split()
                        minute = min_period[0]
                        period = min_period[1]
                    else:
                        minute_period = re.search(r'(\d{2})\s*(AM|PM|am|pm)', period)
                        if minute_period:
                            minute, period = minute_period.groups()
                        else:
                            return number
                    
                    # Clear pronunciation for common time formats
                    if int(minute) == 0:
                        return f'{hour} {period.lower()}'
                    elif int(minute) == 30:
                        return f'{hour} thirty {period.lower()}'
                    else:
                        return f'{hour} {minute} {period.lower()}'
                return number
            
            # Room numbers
            elif re.search(r'\b(room|ward|chamber|cabin)\s+\d+\b', sentence.lower()):
                return f'<say-as interpret-as="characters">{number}</say-as>'
            
            # General numbers up to 4 digits (clear cardinal pronunciation)
            elif len(number) <= 4 and number.isdigit():
                # Improve the pronunciation of numbers like 500
                if number == "500":
                    return "five hundred"
                elif number == "200":
                    return "two hundred"
                elif number == "100":
                    return "one hundred"
                elif number == "1000":
                    return "one thousand"
                else:
                    return f'<say-as interpret-as="cardinal">{number}</say-as>'
            
            # Larger numbers
            else:
                return f'<say-as interpret-as="cardinal">{number}</say-as>'
        
        # Replace all numbers with appropriate say-as tags
        sentence = re.sub(r'\b\d+\b', repl, sentence)
        
        # Handle dates (DD/MM/YYYY format)
        sentence = re.sub(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', repl, sentence)
        
        # Handle times (HH:MM AM/PM format)
        sentence = re.sub(r'\b\d{1,2}:\d{2}\s*(AM|PM|am|pm)\b', repl, sentence)
        
        # Handle times (HH:MM format)
        sentence = re.sub(r'\b\d{1,2}:\d{2}\b', repl, sentence)
        
        # Fix common time pronunciations directly
        sentence = re.sub(r'3(:| )00\s*(PM|pm)', 'three PM', sentence)
        sentence = re.sub(r'2(:| )30\s*(PM|pm)', 'two thirty PM', sentence)
        
        return sentence

    def text_to_ssml_with_emotion(self, text, break_time="350ms"):
        """
        Converts the given text into SSML with emotion, custom pronunciations, and number formatting.
        
        Parameters:
            text (str): The text to convert to SSML
            break_time (str): Duration for pauses between sentences
            
        Returns:
            str: SSML formatted string
        """
        
        # Get the language-specific dictionary based on current language
        lang_specific_dict = {}
        if self.current_language == 'hindi':
            lang_specific_dict = HINDI_PRONUNCIATIONS
        elif self.current_language == 'tamil':
            lang_specific_dict = TAMIL_PRONUNCIATIONS
        
        # Combine with general dictionary
        all_pronunciations = {**PRONUNCIATION_DICTIONARY, **lang_specific_dict}
        
        # Check if text already has SSML tags
        if "<speak>" in text:
            # If so, return with minimal processing
            if not text.startswith("<speak>"):
                text = f"<speak>{text}</speak>"
            return text
        
        # Split text into sentences (for English, Hindi, and Tamil)
        sentences = re.split(r'(?<=[.!?।])\s+', text.strip())
        sentences = [s for s in sentences if s]  # Remove empty strings
        
        ssml_sentences = []
        
        for sentence in sentences:
            # First process numbers
            sentence_with_numbers = self.interpret_numbers(sentence)
            
            # Apply custom pronunciations - but skip Yashoda as we handled it already
            modified_sentence = sentence_with_numbers
            for word, pronunciation_data in all_pronunciations.items():
                # Skip Yashoda for English as we already handled it
                if self.current_language == 'english' and word.lower() in ['yashoda', 'yashodha', 'यशोधा']:
                    continue
                    
                # Apply other pronunciations using regex to ensure whole word matching
                if word in modified_sentence:
                    phoneme = pronunciation_data.get('pronunciation', '')
                    alphabet = pronunciation_data.get('alphabet', 'ipa')
                    if phoneme:
                        phoneme_tag = f'<phoneme alphabet="{alphabet}" ph="{phoneme}">{word}</phoneme>'
                        # Use regex with word boundaries to ensure whole word replacement
                        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                        modified_sentence = pattern.sub(phoneme_tag, modified_sentence)
            
            # Detect the tone and apply appropriate SSML
            tone = self.detect_emotion(sentence)
            
            # Apply SSML styling based on detected tone
            if tone == "urgent":
                # Faster rate, higher pitch, louder volume for urgent messages
                modified = (
                    f'<emphasis level="strong">'
                    f'<prosody rate="110%" pitch="+5%" volume="loud">{modified_sentence}</prosody>'
                    f'</emphasis>'
                )
            elif tone == "empathetic":
                # Warmer, softer voice for empathetic messages
                modified = f'<prosody rate="90%" pitch="-5%" volume="medium">{modified_sentence}</prosody>'
            elif tone == "informative":
                # Clear, measured pace for informational content
                modified = f'<prosody rate="95%" pitch="0%" volume="medium">{modified_sentence}</prosody>'
            elif tone == "greeting":
                # Warm, welcoming tone for greetings
                modified = f'<prosody rate="medium" pitch="5%" volume="medium">{modified_sentence}</prosody>'
            else:  # professional
                # Default professional tone
                modified = f'<prosody rate="medium" pitch="0%">{modified_sentence}</prosody>'
            
            ssml_sentences.append(modified)
        
        # Insert breaks between sentences
        break_tag = f'<break time="{break_time}"/>'
        ssml_body = break_tag.join(ssml_sentences)
        
        # Get language code for SSML
        lang_code = {
            'english': 'en-IN',
            'hindi': 'hi-IN',
            'tamil': 'ta-IN',
            'telugu': 'te-IN'
        }.get(self.current_language, 'en-IN')
        
        # Wrap in <speak> tags with language
        ssml_text = f"""<speak xml:lang="{lang_code}">
  {ssml_body}
</speak>"""
        
        return ssml_text
        
    def text_to_ssml(self, text, break_time="200ms"):
        """
        Legacy method for SSML conversion (preserved for compatibility).
        This now calls the more advanced text_to_ssml_with_emotion method.
        """
        return self.text_to_ssml_with_emotion(text, break_time)
    
    def set_language(self, lang: str) -> None:
        """Set the language for TTS
        Args:
            lang: Language code ('hindi', 'english', 'tamil', or 'telugu')
        """
        if lang in self.voice_config:
            self.current_language = lang
    
    def synthesize(self, text: str) -> bytes:
        """Convert text to audio using Google Cloud TTS
        Args:
            text: Text to convert to speech
        Returns:
            bytes: WAV audio data
        """
        try:
            if not text.strip():  # Check if text is empty or whitespace
                return b""
            
            # Special handling for Yashoda pronunciation in English
            if self.current_language == 'english':
                # Direct text substitution without SSML tags - use phonetic spelling
                text = re.sub(r'\bYashoda\b', 'ya-show-da', text, flags=re.IGNORECASE)
                text = re.sub(r'\bYASHODA\b', 'ya-show-da', text)
                text = re.sub(r'\bYashodha\b', 'ya-show-da', text, flags=re.IGNORECASE)
            
            # Get voice configuration for current language
            voice_config = self.voice_config.get(self.current_language, self.voice_config['english'])
            
            # Generate advanced SSML with emotion, custom pronunciation, and number formatting
            ssml_text = self.text_to_ssml_with_emotion(text)
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=voice_config['language_code'],
                name=voice_config['name'],
                ssml_gender=voice_config['ssml_gender']
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
        self.current_language = 'english'
        self.voice_name = None  # Custom voice name if specified
        
        # Voice configurations for different languages
        self.voice_config = {
            'hindi': {
                'language_code': 'hi-IN',
                'name': 'hi-IN-Wavenet-E',  # Female voice
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            },
            'english': {
                'language_code': 'en-IN',
                'name': 'en-IN-Wavenet-E',  # Female voice
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            },
            'tamil': {
                'language_code': 'ta-IN',
                'name': 'ta-IN-Wavenet-A',  # Female voice
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            },
            'telugu': {
                'language_code': 'te-IN',
                'name': 'te-IN-Standard-A',  # Female voice
                'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
            }
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
    
    def set_language(self, lang: str) -> None:
        """Set the language for TTS
        Args:
            lang: Language code ('hindi', 'english', 'tamil', or 'telugu')
        """
        if lang in self.voice_config:
            self.current_language = lang
    
    def set_voice_name(self, voice_name: str) -> None:
        """Set a specific voice name to use
        Args:
            voice_name: Google Cloud TTS voice name (e.g. 'en-IN-Wavenet-E')
        """
        self.voice_name = voice_name
    
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
            
            # Get voice configuration for current language
            voice_config = self.voice_config.get(self.current_language, self.voice_config['telugu'])
            
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=voice_config['language_code'],
                name=self.voice_name or voice_config['name'],  # Use custom voice name if set
                ssml_gender=voice_config['ssml_gender']
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
            self.language_map = {
                'english': 'en-IN',
                'hindi': 'hi-IN',
                'telugu': 'te-IN',
                'tamil': 'ta-IN',
                'bengali': 'bn-IN',
                'unknown': 'en-IN'  # Default to English for unknown languages
            }
            
            # Reverse mapping for detection
            self.reverse_language_map = {v: k for k, v in self.language_map.items()}
            
        except Exception as e:
            logger.error(f"Error initializing Google STT client: {str(e)}")
            raise

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
            
            # Default language settings
            primary_language_code = 'en-IN'
            alternative_language_codes = ['hi-IN', 'en-IN', 'te-IN']
            
            # If agent_type is provided, get agent-specific language settings
            if agent_type:
                agent_languages = get_agent_languages(agent_type)
                if agent_languages:
                    # Get primary language
                    primary_language_code = agent_languages.get("primary", 'en-IN')
                    
                    # Get supported languages excluding primary
                    supported_languages = agent_languages.get("supported", [])
                    alternative_language_codes = [lang for lang in supported_languages if lang != primary_language_code]
            
            # Get agent-specific speech context phrases if available
            speech_context_phrases = []
            if agent_type:
                speech_context_phrases = get_agent_speech_context(agent_type)
            
            # Configure speech contexts with agent-specific phrases if available
            speech_contexts = []
            if speech_context_phrases:
                speech_contexts = [
                    speech.SpeechContext(
                        phrases=speech_context_phrases,
                        boost=5  # Adjust boost as needed
                    )
                ]
            
            # Configure the recognition settings
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=48000,
                enable_automatic_punctuation=True,
                model='default',  # Can be 'video', 'phone_call', 'command_and_search', etc.
                language_code=primary_language_code,  # Use agent's primary language
                alternative_language_codes=alternative_language_codes,  # Use agent's supported languages
                enable_spoken_emojis=False,
                use_enhanced=True,
                audio_channel_count=1,
                speech_contexts=speech_contexts,
            )
            # Perform the transcription
            response = self.client.recognize(config=config, audio=audio)

            # logger.info("response",response)
            
            if not response.results:
                logger.error("No results from Google STT")
                return "", "unknown"
            
            # Get the transcript from the first result
            transcript = response.results[0].alternatives[0].transcript
            
            # Get the detected language from response
            detected_language_code = response.results[0].language_code
            
            # Convert language code to lowercase for consistent mapping
            if detected_language_code:
                detected_language_code = detected_language_code.lower()
                # Map the language code (e.g., "hi-in") to our language format (e.g., "hindi")
                detected_language = self.reverse_language_map.get(detected_language_code, 'unknown')
                
                # If exact match not found, try matching just the language part (e.g., "hi")
                if detected_language == 'unknown' and '-' in detected_language_code:
                    lang_part = detected_language_code.split('-')[0]
                    for key, value in self.language_map.items():
                        if value.lower().startswith(lang_part):
                            detected_language = key
                            break
            else:
                detected_language = 'unknown'
            
            logger.info(f"Transcribed text: '{transcript}', Detected language: {detected_language} (code: {detected_language_code})")
            return transcript, detected_language
            
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