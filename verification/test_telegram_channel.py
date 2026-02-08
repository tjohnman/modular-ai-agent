import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import time

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_system.channels.telegram_channel import TelegramChannel
from agent_system.core.channel import FileAttachment

class TestTelegramChannel(unittest.TestCase):

    def setUp(self):
        self.token = "test_token"
        self.chat_id = "12345"
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": self.token, "TELEGRAM_CHAT_ID": self.chat_id}):
            self.channel = TelegramChannel()

    @patch("time.sleep", return_value=None)
    def test_get_input_text(self, mock_sleep):
        # Mocking session.get response
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True,
            "result": [
                {
                    "update_id": 100,
                    "message": {
                        "chat": {"id": 12345},
                        "text": "Hello Agent"
                    }
                }
            ]
        }
        self.channel.session.get = MagicMock(return_value=mock_resp)
        
        result = self.channel.get_input()
        self.assertEqual(result, "Hello Agent")
        self.assertEqual(self.channel.offset, 101)

    @patch("time.sleep", return_value=None)
    def test_get_input_restricted(self, mock_sleep):
        # Mocking session.get with a message from a different chat ID then a valid one
        mock_resp_unauthorized = MagicMock()
        mock_resp_unauthorized.json.return_value = {
            "ok": True,
            "result": [
                {
                    "update_id": 100,
                    "message": {
                        "chat": {"id": 99999}, # Different ID
                        "text": "Unauthorized"
                    }
                }
            ]
        }
        
        mock_resp_authorized = MagicMock()
        mock_resp_authorized.json.return_value = {
            "ok": True,
            "result": [
                {
                    "update_id": 101,
                    "message": {
                        "chat": {"id": 12345},
                        "text": "Authorized"
                    }
                }
            ]
        }
        
        self.channel.session.get = MagicMock(side_effect=[mock_resp_unauthorized, mock_resp_authorized])
        
        result = self.channel.get_input()
        self.assertEqual(result, "Authorized")

    def test_send_output(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        self.channel.session.post = MagicMock(return_value=mock_resp)
        
        self.channel.send_output("Test Response")
        self.channel.session.post.assert_called()
        args, kwargs = self.channel.session.post.call_args
        self.assertEqual(kwargs["json"]["text"], "Test Response")
        self.assertEqual(kwargs["json"]["chat_id"], self.chat_id)

    def test_send_file(self):
        # Create a dummy file
        with open("dummy.txt", "w") as f:
            f.write("test content")
        
        try:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"ok": True}
            self.channel.session.post = MagicMock(return_value=mock_resp)
            
            self.channel.send_file("dummy.txt", caption="Here is a file")
            self.channel.session.post.assert_called()
            args, kwargs = self.channel.session.post.call_args
            self.assertIn("sendDocument", args[0])
            self.assertEqual(kwargs["data"]["caption"], "Here is a file")
        finally:
            if os.path.exists("dummy.txt"):
                os.remove("dummy.txt")

    def test_show_activity(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        self.channel.session.post = MagicMock(return_value=mock_resp)
        
        self.channel.show_activity("typing")
        # Give the thread a moment to start and call post
        time.sleep(0.1)
        self.channel.stop_activity()
        
        self.channel.session.post.assert_called()
        args, kwargs = self.channel.session.post.call_args
        self.assertIn("sendChatAction", args[0])
        self.assertEqual(kwargs["json"]["action"], "typing")
        self.assertEqual(kwargs["json"]["chat_id"], self.chat_id)

if __name__ == "__main__":
    unittest.main()
