import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import queue
import time

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_system.core.engine import Engine
from agent_system.core.channel import Channel

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

class TestMultiChannel(unittest.TestCase):

    def setUp(self):
        self.provider = MagicMock()
        self.persistence = MagicMock()
        self.persistence.load_history.return_value = []
        
        self.channel1 = MockChannel("Terminal")
        self.channel2 = MockChannel("Telegram")
        
        self.engine = Engine(
            provider=self.provider,
            channels=[self.channel1, self.channel2],
            persistence=self.persistence
        )

    def test_interleaved_input(self):
        # Setup provider response
        self.provider.generate_response.side_effect = ["Response 1", "Response 2"]
        
        # Start engine in a thread because run() is blocking
        import threading
        engine_thread = threading.Thread(target=self.engine.run, daemon=True)
        engine_thread.start()
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Send input to channel 1
        self.channel1.inputs.put("Hello from 1")
        time.sleep(0.5)
        self.assertIn("AI: Response 1", self.channel1.outputs)
        self.assertIn("ACTIVITY: typing", self.channel1.outputs)
        self.assertEqual(len(self.channel2.outputs), 1) # Just the init message
        
        # Send input to channel 2
        self.channel2.inputs.put("Hello from 2")
        time.sleep(0.5)
        self.assertIn("AI: Response 2", self.channel2.outputs)
        self.assertIn("ACTIVITY: typing", self.channel2.outputs)
        # channel1 should still have its messages: Init + Activity + Response
        self.assertEqual(len(self.channel1.outputs), 3) 

if __name__ == "__main__":
    unittest.main()
