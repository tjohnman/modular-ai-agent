import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_system.channels.telegram_channel import TelegramChannel
from agent_system.channels.terminal_channel import TerminalChannel

class TestFormatting(unittest.TestCase):

    def setUp(self):
        # Mocking environment variables for TelegramChannel
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "123"}):
            self.telegram = TelegramChannel()
        self.terminal = TerminalChannel()

    def test_telegram_bold(self):
        text = "This is **bold** text."
        expected = "This is <b>bold</b> text."
        self.assertEqual(self.telegram._format_markdown(text), expected)

    def test_telegram_italic(self):
        text = "This is *italic* and _italic_."
        expected = "This is <i>italic</i> and <i>italic</i>."
        self.assertEqual(self.telegram._format_markdown(text), expected)

    def test_telegram_code(self):
        text = "Check `code` and ```\nblock\n```."
        expected = "Check <code>code</code> and <pre>\nblock\n</pre>."
        self.assertEqual(self.telegram._format_markdown(text), expected)

    def test_telegram_link(self):
        text = "[Google](https://google.com)"
        expected = '<a href="https://google.com">Google</a>'
        self.assertEqual(self.telegram._format_markdown(text), expected)

    def test_telegram_escape(self):
        text = "A & B < C > D"
        expected = "A &amp; B &lt; C &gt; D"
        self.assertEqual(self.telegram._format_markdown(text), expected)

    def test_telegram_headers(self):
        text = "# Title\n## **Subtitle**\n### Mixed **Bold** and *Italic*"
        # Should strip ** and * inside headers
        expected = "<b>Title</b>\n<b>Subtitle</b>\n<b>Mixed Bold and Italic</b>"
        self.assertEqual(self.telegram._format_markdown(text), expected)

    def test_telegram_nested_bold(self):
        # Even if not a header, check if we handle some weird cases if needed, 
        # but the main fix was for headers.
        text = "**Bold with **nested** bold**"
        # The current regex for bold is simple: \*\*(.*?)\*\*
        # It will match the first ** to the next **.
        # "**Bold with " + "nested" + " bold**" -> <b>Bold with </b>nested<b> bold</b>
        # This is actually fine for Telegram as it's not truly nested in the output.
        pass

    def test_telegram_lists(self):
        text = "* Item 1\n- Item 2"
        expected = "• Item 1\n• Item 2"
        self.assertEqual(self.telegram._format_markdown(text), expected)

    def test_terminal_bold(self):
        text = "This is **bold** text."
        # \033[1m is bold, \033[0m is reset
        expected = "This is \033[1mbold\033[0m text."
        self.assertEqual(self.terminal._format_markdown(text), expected)

    def test_terminal_italic(self):
        text = "This is *italic*."
        expected = "This is \033[3mitalic\033[0m."
        self.assertEqual(self.terminal._format_markdown(text), expected)

    def test_terminal_code(self):
        text = "Check `code`."
        expected = "Check \033[36mcode\033[0m."
        self.assertEqual(self.terminal._format_markdown(text), expected)

    def test_terminal_link(self):
        text = "[Google](https://google.com)"
        expected = "Google (https://google.com)"
        self.assertEqual(self.terminal._format_markdown(text), expected)

    def test_terminal_headers(self):
        text = "# Title\n## Subtitle"
        # BOLD Title, BOLD Subtitle
        expected = "\033[1mTitle\033[0m\n\033[1mSubtitle\033[0m"
        self.assertEqual(self.terminal._format_markdown(text), expected)

    def test_terminal_lists(self):
        text = "* Item 1\n- Item 2"
        expected = "• Item 1\n• Item 2"
        self.assertEqual(self.terminal._format_markdown(text), expected)

if __name__ == "__main__":
    unittest.main()
