import unittest
from unittest.mock import MagicMock, patch
import time
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_system.channels.telegram_channel import TelegramChannel

class TestTelegramPersistentIndicators(unittest.TestCase):

    def setUp(self):
        self.token = "test_token"
        self.chat_id = "12345"
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": self.token, "TELEGRAM_CHAT_ID": self.chat_id}):
            self.channel = TelegramChannel()

    def test_show_activity_periodic(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        self.channel.session.post = MagicMock(return_value=mock_resp)
        
        # Start activity
        self.channel.show_activity("typing")
        
        # Wait for at least two pulses (loop is 4s, let's wait 5s)
        time.sleep(5)
        
        # Stop activity
        self.channel.stop_activity()
        
        # Should have called at least twice
        self.assertGreaterEqual(self.channel.session.post.call_count, 2)
        
        # Check payload
        last_call_args = self.channel.session.post.call_args_list[0]
        self.assertEqual(last_call_args[1]["json"]["action"], "typing")
        self.assertEqual(last_call_args[1]["json"]["chat_id"], self.chat_id)

    def test_stop_activity_on_send(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        self.channel.session.post = MagicMock(return_value=mock_resp)
        
        # Start activity
        self.channel.show_activity("typing")
        self.assertTrue(self.channel.active_activity == "typing")
        
        # Sending output should stop activity
        self.channel.send_output("Hello")
        self.assertIsNone(self.channel.active_activity)
        self.assertTrue(self.channel.stop_activity_event.is_set())

if __name__ == "__main__":
    unittest.main()
