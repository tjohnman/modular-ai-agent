
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_system.core.engine import Engine

class TestCompactLogic(unittest.TestCase):
    def setUp(self):
        self.mock_provider = MagicMock()
        self.mock_channel = MagicMock()
        self.mock_persistence = MagicMock()
        
        # Mock provider usage
        self.mock_provider.get_usage.return_value = {"total_tokens": 100}
        
        # Initialize Engine with mocks
        self.engine = Engine(
            provider=self.mock_provider,
            channels=[self.mock_channel],
            persistence=self.mock_persistence,
            system_prompt_path="non_existent_path"
        )

    def test_handle_compact_logic(self):
        # 1. Setup a history with 10 turns
        history = [
            {"role": "user", "content": f"Turn {i}"} for i in range(10)
        ]
        self.mock_persistence.load_history.return_value = history
        
        # 2. Mock provider response for summary
        self.mock_provider.generate_response.return_value = "This is a summary of turns 0-3."
        
        # 3. Call handle_compact
        self.engine._handle_compact()
        
        # 4. Verify what was sent to replace_history
        self.mock_persistence.replace_history.assert_called_once()
        new_history = self.mock_persistence.replace_history.call_args[0][0]
        
        # Expected new_history structure:
        # [0]: Summary turn (system)
        # [1]: Awareness turn (system)
        # [2-7]: Last 6 turns intact
        
        self.assertEqual(len(new_history), 2 + 6)
        self.assertEqual(new_history[0]["role"], "system")
        self.assertIn("Summary of previous conversation", new_history[0]["content"])
        self.assertIn("This is a summary of turns 0-3.", new_history[0]["content"])
        
        self.assertEqual(new_history[1]["role"], "system")
        self.assertIn("compacted", new_history[1]["content"])
        
        # Check last 6 turns (indices 4, 5, 6, 7, 8, 9)
        for i in range(6):
            self.assertEqual(new_history[i+2], history[i+4])
            self.assertEqual(new_history[i+2]["content"], f"Turn {i+4}")

    def test_handle_compact_insufficient_history(self):
        # History with 6 or fewer turns should not be compacted
        history = [{"role": "user", "content": f"Turn {i}"} for i in range(6)]
        self.mock_persistence.load_history.return_value = history
        
        self.engine._handle_compact()
        
        # replace_history should NOT be called
        self.mock_persistence.replace_history.assert_not_called()

if __name__ == "__main__":
    unittest.main()
