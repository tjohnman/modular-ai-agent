import os
import sys
import unittest
import shutil
import tempfile
import json
from datetime import datetime

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.persistence import Persistence

class TestSessionManagement(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for sessions
        self.test_dir = tempfile.mkdtemp()
        self.persistence = Persistence(sessions_dir=self.test_dir)

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_start_new_session_with_title(self):
        title = "Test Session Title"
        self.persistence.start_new_session(title=title)
        
        sessions = self.persistence.list_sessions()
        self.assertEqual(len(sessions), 2) # One from __init__, one from start_new_session
        self.assertEqual(sessions[-1]["title"], title)

    def test_set_session_title(self):
        title = "Renamed Session"
        self.persistence.set_session_title(title)
        
        sessions = self.persistence.list_sessions()
        self.assertEqual(sessions[-1]["title"], title)

    def test_list_sessions(self):
        self.persistence.start_new_session(title="Session 1")
        self.persistence.start_new_session(title="Session 2")
        
        sessions = self.persistence.list_sessions()
        self.assertEqual(len(sessions), 3) # Initial + 2 more
        self.assertEqual(sessions[1]["title"], "Session 1")
        self.assertEqual(sessions[2]["title"], "Session 2")
        self.assertEqual(sessions[1]["index"], 1)
        self.assertEqual(sessions[2]["index"], 2)

    def test_switch_session(self):
        # Create first session and save a message
        self.persistence.set_session_title("First Session")
        self.persistence.save_message("user", "Hello first")
        
        # Create second session and save a message
        self.persistence.start_new_session(title="Second Session")
        self.persistence.save_message("user", "Hello second")
        
        # Verify history in second session
        history = self.persistence.load_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["content"], "Hello second")
        
        # Switch to first session
        success = self.persistence.switch_session(0)
        self.assertTrue(success)
        
        # Verify history in first session
        history = self.persistence.load_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["content"], "Hello first")

    def test_load_history_filters_metadata(self):
        self.persistence.save_message("user", "Regular message")
        self.persistence.set_session_title("Some Title")
        self.persistence.save_message("assistant", "Response")
        
        history = self.persistence.load_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    def test_has_title(self):
        self.assertFalse(self.persistence.has_title())
        self.persistence.set_session_title("Title")
        self.assertTrue(self.persistence.has_title())

from unittest.mock import MagicMock, patch
from agent_system.core.engine import Engine

class TestEngineAutoTitling(unittest.TestCase):
    @patch("agent_system.core.engine.logger")
    def test_auto_titling_on_first_message(self, mock_logger):
        provider = MagicMock()
        channel = MagicMock()
        persistence = MagicMock()
        
        # Setup mocks
        persistence.has_title.return_value = False
        provider.generate_response.return_value = "Auto Title"
        
        # We need to mock _load_system_prompt and load_tools to init Engine
        with patch.object(Engine, "_load_system_prompt", return_value="System Prompt"):
            with patch.object(Engine, "load_tools"):
                engine = Engine(provider=provider, channels=[channel], persistence=persistence)
                engine.current_channel = channel
                
                # Simulate first user message
                # Mock the input queue and stop activity to avoid infinite loop
                engine.input_queue = MagicMock()
                engine.input_queue.get.side_effect = [(channel, "First message"), KeyboardInterrupt]
                
                try:
                    engine.run()
                except KeyboardInterrupt:
                    pass
                
                # Verify auto-titling was triggered
                persistence.set_session_title.assert_called_with("Auto Title")
                provider.generate_response.assert_called()

if __name__ == "__main__":
    unittest.main()
