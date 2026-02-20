import os
from faster_whisper import WhisperModel
from agent_system.utils import logger

# The SCHEMA for the Google GenAI tool definition
SCHEMA = {
    "name": "transcribe_audio",
    "display_name": "Transcribing audio",
    "description": "Transcribes an audio file into text using the Whisper model. Highly efficient and optimized for CPU execution.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "audio_file": {
                "type": "STRING",
                "description": "The filename of the audio file in the workspace (e.g., 'voice_12345.ogg')."
            },
            "model_size": {
                "type": "STRING",
                "enum": ["tiny", "base", "small", "medium"],
                "default": "base",
                "description": "The Whisper model size. 'base' is the recommended default for Raspberry Pi 4 (good balance of speed/accuracy). Use 'small' or 'medium' for higher accuracy at the cost of processing time."
            },
            "language": {
                "type": "STRING",
                "description": "Optional language code to guide transcription (e.g., 'en', 'es', 'fr'). If omitted, language is auto-detected."
            }
        },
        "required": ["audio_file"]
    }
}

def execute(params: dict) -> str:
    """Executes the transcription tool."""
    audio_filename = params.get("audio_file")
    model_size = params.get("model_size", "base")
    language = params.get("language")
    workspace_dir = params.get("_workspace") # Injected by the Engine
    
    if not workspace_dir:
        return "Error: Workspace directory not found. Tool must be run via the Agent Engine."

    audio_path = os.path.join(workspace_dir, audio_filename)
    if not os.path.exists(audio_path):
        return f"Error: Audio file '{audio_filename}' not found in workspace."

    try:
        logger.info(f"[Tool: transcribe_audio] Starting transcription of {audio_filename} using {model_size} model...")
        
        # Load model on CPU (optimized for low-spec systems)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        transcribe_kwargs = {"beam_size": 5}
        if language:
            transcribe_kwargs["language"] = language

        segments, info = model.transcribe(audio_path, **transcribe_kwargs)
        
        transcription = ""
        for segment in segments:
            transcription += f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}\n"
            
        if not transcription.strip():
            return "Transcription completed, but no speech was detected."
            
        result = (
            f"Transcription of '{audio_filename}' (Detected Language: {info.language} with probability {info.language_probability:.4f}):\n\n"
            f"{transcription}"
        )
        
        logger.info(f"[Tool: transcribe_audio] Transcription successful.")
        return result
        
    except Exception as e:
        error_msg = f"An error occurred during transcription: {str(e)}"
        logger.error(f"[Tool: transcribe_audio] {error_msg}")
        return error_msg
