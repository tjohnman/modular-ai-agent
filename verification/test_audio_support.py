import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import queue
import time

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_system.core.engine import Engine
from agent_system.core.channel import Channel, FileAttachment

class MockChannel(Channel):
    def __init__(self, name):
        self.name = name
        self.outputs = []
        self.inputs = queue.Queue()

    def get_input(self):
        return self.inputs.get()

    def send_output(self, text):
        self.outputs.append(text)

    def send_file(self, file_path, caption=None):
        self.outputs.append(f"FILE: {file_path}")

    def show_activity(self, action="typing"):
        self.outputs.append(f"ACTIVITY: {action}")

    def send_status(self, text):
        self.outputs.append(f"STATUS: {text}")

class TestAudioSupport(unittest.TestCase):

    def setUp(self):
        self.provider = MagicMock()
        self.persistence = MagicMock()
        self.persistence.load_history.return_value = []
        
        self.channel = MockChannel("Test")
        
        self.workspace_dir = os.path.abspath("test_audio_workspace")
        self.engine = Engine(
            provider=self.provider,
            channels=[self.channel],
            persistence=self.persistence,
            workspace_dir=self.workspace_dir
        )
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir)

    def tearDown(self):
        import shutil
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)

    def test_audio_upload_triggers_turn(self):
        # Create a mock FileAttachment with audio mime type
        audio_attachment = FileAttachment(
            name="voice.ogg",
            content_getter=lambda: b"fake audio data",
            mime_type="audio/ogg"
        )
        
        # Setup provider to return a simple response
        self.provider.generate_response.return_value = "I heard your audio."
        
        # Start engine in a thread
        import threading
        engine_thread = threading.Thread(target=self.engine.run, daemon=True)
        engine_thread.start()
        
        time.sleep(0.5)
        
        # Send audio attachment
        self.channel.inputs.put(audio_attachment)
        time.sleep(1) # Give it time to process and call provider
        
        # Verify persistence call for USER message (triggers turn)
        expected_path = os.path.join(self.workspace_dir, "voice.ogg")
        self.persistence.save_message.assert_any_call(
            "user", 
            "[Uploaded voice.ogg]",
            parts=[{'file_path': expected_path, 'mime_type': 'audio/ogg'}]
        )
        
        # Verify provider was CALLED
        self.provider.generate_response.assert_called()
        
        # Verify response was sent back to channel
        self.assertTrue(any("I heard your audio." in o for o in self.channel.outputs))

    def test_generic_file_upload_silent(self):
        # Create a mock FileAttachment with generic mime type
        doc_attachment = FileAttachment(
            name="data.csv",
            content_getter=lambda: b"1,2,3",
            mime_type="text/csv"
        )
        
        # Start engine in a thread
        import threading
        engine_thread = threading.Thread(target=self.engine.run, daemon=True)
        engine_thread.start()
        
        time.sleep(0.5)
        
        # Send doc attachment
        self.channel.inputs.put(doc_attachment)
        time.sleep(0.5)
        
        # Verify persistence call for SYSTEM message (silent)
        self.persistence.save_message.assert_any_call(
            "system", 
            "SYSTEM: User uploaded file 'data.csv'. It has been saved to the workspace."
        )
        
        # Verify provider was NOT called
        self.provider.generate_response.assert_not_called()

if __name__ == "__main__":
    unittest.main()
