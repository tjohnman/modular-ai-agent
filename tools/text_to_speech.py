import os
import wave
import time
import platform
import requests
from piper import PiperVoice
from agent_system.utils import logger

# Default model configuration
DEFAULT_MODEL_NAME = "en_US-lessac-medium"
MODEL_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/"

def download_file(url: str, dest_path: str):
    """Downloads a file from a URL to a destination path."""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

# The SCHEMA for the Google GenAI tool definition
SCHEMA = {
    "name": "text_to_speech",
    "display_name": "Text to Speech",
    "description": "Converts text into speech audio (WAV format) using the Piper TTS engine. Optimized for low-spec environments.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {
                "type": "STRING",
                "description": "The text to convert to speech."
            },
            "output_file": {
                "type": "STRING",
                "description": "The desired filename for the output WAV file (e.g., 'response.wav'). Defaults to 'speech_<timestamp>.wav'."
            },
            "voice": {
                "type": "STRING",
                "description": "The name or path of the Piper voice model to use. If not provided, a default voice will be used.",
                "default": "en_US-lessac-medium"
            }
        },
        "required": ["text"]
    }
}

def execute(params: dict) -> str:
    """Executes the text-to-speech tool."""
    text = params.get("text")
    output_filename = params.get("output_file")
    voice_name = params.get("voice", "en_US-lessac-medium")
    workspace_dir = params.get("_workspace") # Injected by the Engine
    
    if not workspace_dir:
        return "Error: Workspace directory not found. Tool must be run via the Agent Engine."

    if not output_filename:
        output_filename = f"speech_{int(time.time())}.wav"
    
    if not output_filename.endswith(".wav"):
        output_filename += ".wav"

    # 1. Architecture Detection
    arch = platform.machine()
    logger.info(f"[Tool: text_to_speech] Detected architecture: {arch}")

    # 2. Model Management
    models_dir = os.path.join(workspace_dir, "models")
    model_path = os.path.join(models_dir, f"{DEFAULT_MODEL_NAME}.onnx")
    config_path = f"{model_path}.json"

    try:
        # Check and download model if missing
        if not os.path.exists(model_path):
            logger.info(f"[Tool: text_to_speech] Downloading model {DEFAULT_MODEL_NAME}.onnx...")
            download_file(f"{MODEL_BASE_URL}{DEFAULT_MODEL_NAME}.onnx", model_path)
        
        if not os.path.exists(config_path):
            logger.info(f"[Tool: text_to_speech] Downloading config {DEFAULT_MODEL_NAME}.onnx.json...")
            download_file(f"{MODEL_BASE_URL}{DEFAULT_MODEL_NAME}.onnx.json", config_path)

        # 3. Speech Synthesis
        voice = PiperVoice.load(model_path)
        
        # Ensure output directory exists within workspace
        output_dir = os.path.join(workspace_dir, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        full_output_path = os.path.join(output_dir, output_filename)
        
        with wave.open(full_output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2) # 16-bit
            wav_file.setframerate(voice.config.sample_rate)
            for chunk in voice.synthesize(text):
                wav_file.writeframes(chunk.audio_int16_bytes)
            
        logger.info(f"[Tool: text_to_speech] Audio saved to {full_output_path}")
        
        return f"Successfully generated speech audio for: '{text}'. File: {output_filename}. (Architecture: {arch})"
        
    except Exception as e:
        error_msg = f"An error occurred during TTS: {str(e)}"
        logger.error(f"[Tool: text_to_speech] {error_msg}")
        return error_msg
