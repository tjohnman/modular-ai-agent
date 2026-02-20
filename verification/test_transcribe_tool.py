import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.transcribe_audio import execute

class TestTranscribeAudio(unittest.TestCase):

    def setUp(self):
        self.workspace = "test_transcribe_workspace"
        if not os.path.exists(self.workspace):
            os.makedirs(self.workspace)
        
        self.audio_file = "test_voice.ogg"
        self.audio_path = os.path.join(self.workspace, self.audio_file)
        with open(self.audio_path, "wb") as f:
            f.write(b"fake audio data")

    def tearDown(self):
        import shutil
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

    @patch("tools.transcribe_audio.WhisperModel")
    def test_transcribe_success(self, mock_whisper):
        # Setup mock segments
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 1.5
        mock_segment.text = "Hello world"
        
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99
        
        mock_model_instance = MagicMock()
        mock_model_instance.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model_instance
        
        params = {
            "audio_file": self.audio_file,
            "_workspace": self.workspace
        }
        
        result = execute(params)
        
        self.assertIn("Transcription of 'test_voice.ogg'", result)
        self.assertIn("Hello world", result)
        self.assertIn("Detected Language: en", result)
        mock_model_instance.transcribe.assert_called_once_with(self.audio_path, beam_size=5)

    @patch("tools.transcribe_audio.WhisperModel")
    def test_transcribe_with_language(self, mock_whisper):
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.text = "Hola"

        mock_info = MagicMock()
        mock_info.language = "es"
        mock_info.language_probability = 0.95

        mock_model_instance = MagicMock()
        mock_model_instance.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model_instance

        params = {
            "audio_file": self.audio_file,
            "language": "es",
            "_workspace": self.workspace
        }

        result = execute(params)
        self.assertIn("Detected Language: es", result)
        mock_model_instance.transcribe.assert_called_once_with(self.audio_path, beam_size=5, language="es")

    def test_file_not_found(self):
        params = {
            "audio_file": "missing.ogg",
            "_workspace": self.workspace
        }
        result = execute(params)
        self.assertIn("Error: Audio file 'missing.ogg' not found", result)

    def test_no_workspace(self):
        params = {
            "audio_file": self.audio_file
        }
        result = execute(params)
        self.assertIn("Error: Workspace directory not found", result)

if __name__ == "__main__":
    unittest.main()
