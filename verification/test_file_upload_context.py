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

class TestFileUploadContext(unittest.TestCase):

    def setUp(self):
        self.provider = MagicMock()
        self.persistence = MagicMock()
        self.persistence.load_history.return_value = []
        
        self.channel = MockChannel("Test")
        
        self.engine = Engine(
            provider=self.provider,
            channels=[self.channel],
            persistence=self.persistence,
            workspace_dir="test_workspace"
        )
        if not os.path.exists("test_workspace"):
            os.makedirs("test_workspace")

    def tearDown(self):
        import shutil
        if os.path.exists("test_workspace"):
            shutil.rmtree("test_workspace")

    def test_file_upload_saves_system_message(self):
        # Create a mock FileAttachment
        file_attachment = FileAttachment(
            name="test.txt",
            content_getter=lambda: b"hello world"
        )
        
        # Start engine in a thread
        import threading
        engine_thread = threading.Thread(target=self.engine.run, daemon=True)
        engine_thread.start()
        
        time.sleep(0.5)
        
        # Send file attachment
        self.channel.inputs.put(file_attachment)
        time.sleep(0.5)
        
        # Verify persistence call
        self.persistence.save_message.assert_called_with(
            "system", 
            "SYSTEM: User uploaded file 'test.txt'. It has been saved to the workspace."
        )
        
        # Verify provider was NOT called (no model turn)
        self.provider.generate_response.assert_not_called()
        
        # Verify no output was sent to the channel (init message and activity excluded)
        # channel.outputs[0] is initialized message
        # new: channel.outputs[1] is ACTIVITY: upload_document
        relevant_outputs = [o for o in self.channel.outputs if not o.startswith("AI Agent System initialized") and "upload_document" not in o]
        self.assertEqual(len(relevant_outputs), 0)

if __name__ == "__main__":
    unittest.main()
