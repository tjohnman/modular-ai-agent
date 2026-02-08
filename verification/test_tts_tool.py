import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.text_to_speech import execute

class TestTextToSpeech(unittest.TestCase):

    def setUp(self):
        self.workspace = "test_tts_workspace"
        if not os.path.exists(self.workspace):
            os.makedirs(self.workspace)
        
        # Create a mock model directory
        self.models_dir = os.path.join(self.workspace, "models", "piper")
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.voice_name = "en_US-lessac-medium"
        self.model_path = os.path.join(self.models_dir, f"{self.voice_name}.onnx")
        with open(self.model_path, "w") as f:
            f.write("fake model data")

    def tearDown(self):
        import shutil
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

    @patch("tools.text_to_speech.PiperVoice")
    @patch("tools.text_to_speech.download_file")
    @patch("os.path.exists")
    @patch("wave.open")
    @patch("piper.PiperVoice")
    def test_tts_success(self, mock_piper_voice_lib, mock_wave_open, mock_exists, mock_download, mock_piper_voice_tool):
        # Setup mocks
        mock_exists.return_value = True # Assume files exist to avoid download call
        mock_voice_instance = MagicMock()
        mock_chunk1 = MagicMock()
        mock_chunk1.audio_int16_bytes = b"chunk1"
        mock_chunk2 = MagicMock()
        mock_chunk2.audio_int16_bytes = b"chunk2"
        mock_voice_instance.synthesize.return_value = [mock_chunk1, mock_chunk2]
        mock_piper_voice_tool.load.return_value = mock_voice_instance
        
        params = {
            "text": "Hello world",
            "output_file": "test.wav",
            "_workspace": self.workspace
        }
        
        result = execute(params)
        
        self.assertIn("Successfully generated speech audio", result)
        self.assertIn("test.wav", result)
        self.assertIn("Architecture", result)
        
        # Verify wave.open was called with the correct output path
        expected_path = os.path.join(self.workspace, "output", "test.wav")
        mock_wave_open.assert_called_once_with(expected_path, "wb")
        
        mock_piper_voice_tool.load.assert_called_once()
        mock_voice_instance.synthesize.assert_called_once_with("Hello world")
        mock_wave_open.assert_called_once()
        
        # Verify WAV parameters were set
        mock_wave_file = mock_wave_open.return_value.__enter__.return_value
        mock_wave_file.setnchannels.assert_called_with(1)
        mock_wave_file.setsampwidth.assert_called_with(2)
        mock_wave_file.setframerate.assert_called()
        
        # Verify frames were written
        mock_wave_file.writeframes.assert_any_call(b"chunk1")
        mock_wave_file.writeframes.assert_any_call(b"chunk2")

    @patch("tools.text_to_speech.requests.get")
    def test_download_failed(self, mock_get):
        # Setup mock to raise error on download
        mock_get.side_effect = Exception("Connection error")
        
        params = {
            "text": "Hello",
            "_workspace": self.workspace
        }
        
        # We need to make sure os.path.exists returns False to trigger download
        with patch("os.path.exists", return_value=False):
            result = execute(params)
            self.assertIn("An error occurred during TTS: Connection error", result)

    def test_no_workspace(self):
        params = {
            "text": "Hello"
        }
        result = execute(params)
        self.assertIn("Error: Workspace directory not found", result)

if __name__ == "__main__":
    unittest.main()
