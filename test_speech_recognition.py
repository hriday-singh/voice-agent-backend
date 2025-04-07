import os
import io
import argparse
import json
from dotenv import load_dotenv
from app.utils.speech_service import GoogleSTT
from app.utils.agent_config import get_agent_by_id, get_agent_languages
import wave
import numpy as np
import sounddevice as sd
import logging
import tempfile
import subprocess
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def check_google_credentials():
    """Check if Google credentials are properly set up"""
    api_key = os.getenv('GOOGLE_API_KEY')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if api_key:
        logger.info("Using Google API key authentication.")
        return True
    elif credentials_path:
        if os.path.exists(credentials_path):
            logger.info(f"Using Google service account credentials from: {credentials_path}")
            # Verify the credentials file is valid JSON
            try:
                with open(credentials_path, 'r') as f:
                    json.load(f)
                return True
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in credentials file: {credentials_path}")
                return False
        else:
            logger.error(f"Credentials file not found: {credentials_path}")
            return False
    else:
        logger.error("No Google credentials found. Set either GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS.")
        return False

def record_audio(duration=5, sample_rate=48000, save_path=None):
    """
    Record audio from microphone and optionally save to file
    
    Args:
        duration: Duration in seconds to record
        sample_rate: Sample rate for recording
        save_path: Path to save the recorded audio (optional)
        
    Returns:
        audio_data: Audio data as bytes in WAV format
    """
    print(f"Recording for {duration} seconds...")
    try:
        # Record with higher quality settings
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='int16'
        )
        sd.wait()  # Wait until recording is finished
        print("Recording finished.")
        
        # First save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.close()
        
        # Use wave to write proper WAV format
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
        
        # Read back the file
        with open(temp_file.name, 'rb') as f:
            audio_bytes = f.read()
        
        # If save_path is provided, save a copy of the recording
        if save_path:
            # Create directory if it doesn't exist
            save_dir = os.path.dirname(save_path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            # Copy the temp file to the destination
            with open(save_path, 'wb') as f:
                f.write(audio_bytes)
            print(f"Recording saved to: {save_path}")
        
        # Clean up temp file
        os.unlink(temp_file.name)
        
        byte_io = io.BytesIO(audio_bytes)
        return byte_io
    except Exception as e:
        logger.error(f"Error recording audio: {str(e)}")
        raise

def load_audio_file(file_path):
    """
    Load audio from a file
    
    Args:
        file_path: Path to audio file
        
    Returns:
        audio_data: Audio data as bytes in WAV format
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Convert non-WAV files to WAV format if needed
        if not file_path.lower().endswith('.wav'):
            logger.info(f"Converting {file_path} to WAV format...")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()
            
            # Use ffmpeg to convert
            try:
                subprocess.run([
                    'ffmpeg', '-i', file_path, 
                    '-acodec', 'pcm_s16le', 
                    '-ac', '1', 
                    '-ar', '48000', 
                    temp_file.name
                ], check=True)
                
                with open(temp_file.name, 'rb') as f:
                    audio_bytes = f.read()
                
                # Clean up
                os.unlink(temp_file.name)
                return io.BytesIO(audio_bytes)
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.error(f"Error converting audio: {str(e)}")
                # Fall back to direct reading
                os.unlink(temp_file.name)
                logger.info("Falling back to direct file reading.")
        
        # Read the file directly
        with open(file_path, 'rb') as f:
            return io.BytesIO(f.read())
    except Exception as e:
        logger.error(f"Error loading audio file: {str(e)}")
        raise

def print_agent_language_config(agent_id):
    """
    Print language configuration for a specific agent
    
    Args:
        agent_id: Agent ID (e.g., 'realestate', 'hospital')
    """
    agent_config = get_agent_by_id(agent_id)
    if not agent_config:
        print(f"Agent '{agent_id}' not found.")
        return
    
    languages = agent_config.get("languages", {})
    primary = languages.get("primary", "en-IN")
    supported = languages.get("supported", [])
    
    print(f"\nAgent: {agent_config.get('name', agent_id)}")
    print(f"Primary language: {primary}")
    print(f"Supported languages: {', '.join(supported)}")
    
    # Also print model config
    model_config = agent_config.get("model_config", {})
    if model_config:
        print(f"Model provider: {model_config.get('provider', 'unknown')}")
        print(f"Model name: {model_config.get('name', 'unknown')}")

def test_stt(audio_data, agent_id=None):
    """
    Test Speech-to-Text with optional agent-specific settings
    
    Args:
        audio_data: Audio data as bytes in WAV format
        agent_id: Agent ID for language configuration (optional)
    """
    # Check Google credentials first
    if not check_google_credentials():
        print("ERROR: Google credentials not properly configured.")
        print("Please set GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS environment variable.")
        return None, None
        
    # Initialize Google STT
    try:
        stt = GoogleSTT()
    except Exception as e:
        print(f"ERROR initializing Google STT: {str(e)}")
        return None, None
    
    # Print agent language config if specified
    if agent_id:
        print_agent_language_config(agent_id)
    
    # Get a copy of the audio data in case we need multiple passes
    audio_copy = io.BytesIO(audio_data.getvalue())
    audio_data.seek(0)
    
    # Transcribe audio with verbose output
    print("\nTranscribing audio...")
    try:
        transcript, detected_language = stt.transcribe(audio_data, agent_id)
        
        # If no transcript, try again without agent settings
        if not transcript and agent_id:
            print("No transcript detected with agent settings, trying without agent settings...")
            audio_copy.seek(0)
            transcript, detected_language = stt.transcribe(audio_copy, None)
        
        print(f"Transcript: {transcript}")
        print(f"Detected language: {detected_language}")
        
        return transcript, detected_language
    except Exception as e:
        print(f"ERROR transcribing audio: {str(e)}")
        logger.error(f"Transcription error: {str(e)}", exc_info=True)
        return None, None

def main():
    parser = argparse.ArgumentParser(description='Test Google Speech-to-Text with agent-specific language configurations')
    
    # Command line arguments
    parser.add_argument('--agent', choices=['realestate', 'hospital'], help='Agent ID to use for language configuration')
    parser.add_argument('--file', help='Path to audio file to transcribe (WAV format preferred)')
    parser.add_argument('--duration', type=int, default=5, help='Duration in seconds to record (default: 5)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--save', help='Save recorded audio to specified path (e.g., "recordings/test.wav")')
    parser.add_argument('--auto-save', action='store_true', help='Automatically save recording with timestamp')
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Print environment status
    print("Testing Google Speech-to-Text")
    print(f"Python version: {os.sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    try:
        # Get audio data (either from file or recording)
        if args.file:
            print(f"Loading audio from file: {args.file}")
            audio_data = load_audio_file(args.file)
        else:
            # Determine save path
            save_path = None
            if args.save:
                save_path = args.save
            elif args.auto_save:
                # Create recordings directory if it doesn't exist
                recordings_dir = os.path.join(os.getcwd(), "recordings")
                if not os.path.exists(recordings_dir):
                    os.makedirs(recordings_dir)
                
                # Generate filename with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                agent_suffix = f"_{args.agent}" if args.agent else ""
                save_path = os.path.join(recordings_dir, f"recording{agent_suffix}_{timestamp}.wav")
            
            # Record with optional save
            audio_data = record_audio(duration=args.duration, save_path=save_path)
        
        # Test STT with agent-specific configuration
        test_stt(audio_data, args.agent)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        logger.error("Test failed with error", exc_info=True)

if __name__ == "__main__":
    main() 