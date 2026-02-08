import os
import re
from typing import Union, Optional
from agent_system.core.channel import Channel, FileAttachment
from agent_system.utils import logger

class TerminalChannel(Channel):
    """Implementation of I/O via the terminal."""
    
    def get_input(self) -> Union[str, FileAttachment]:
        user_input = input("> ")
        
        # Handle /file <path> command
        if user_input.startswith("/file "):
            # Slicing explicitly to avoid lint complaints if any, though it's standard
            parts = user_input.split(" ", 1)
            if len(parts) > 1:
                file_path = parts[1].strip()
            if os.path.exists(file_path) and os.path.isfile(file_path):
                filename = os.path.basename(file_path)
                
                def getter():
                    with open(file_path, "rb") as f:
                        return f.read()
                
                return FileAttachment(name=filename, content_getter=getter)
            else:
                logger.error(f"File not found at {file_path}")
                return self.get_input() # Retry
                
        return user_input
    
    def send_output(self, text: str):
        formatted_text = self._format_markdown(text)
        print(f"AI: {formatted_text}")

    def send_file(self, file_path: str, caption: Optional[str] = None):
        if caption:
            formatted_caption = self._format_markdown(caption)
            print(f"AI: {formatted_caption}")
        
        # In a real terminal channel, we might copy this to a specific output dir
        # or just print the path. For now, let's inform the user.
        logger.info(f"[File Sent: {file_path}]")

    def show_activity(self, action: str = "typing"):
        """Terminal doesn't have a native typing indicator, but we could log it."""
        pass

    def send_status(self, text: str):
        """Prints status updates to the terminal."""
        print(f"[{text}]")

    def _format_markdown(self, text: str) -> str:
        """Converts basic Markdown to Terminal ANSI escape codes."""
        # Reset code
        reset = "\033[0m"
        bold = "\033[1m"
        italic = "\033[3m"
        cyan = "\033[36m"
        
        # 1. Bold: **text** -> \033[1mtext\033[0m
        text = re.sub(r'\*\*(.*?)\*\*', f'{bold}\\1{reset}', text)

        # 2. Italic: *text* or _text_ -> \033[3mtext\033[0m
        text = re.sub(r'(?<!\*)\*([^\s\*].*?[^\s\*])\*(?!\*)', f'{italic}\\1{reset}', text)
        text = re.sub(r'(?<!_)_([^\s_].*?[^\s_])_(?!_)', f'{italic}\\1{reset}', text)

        # 3. Code blocks: ```code``` -> \033[36mcode\033[0m (Cyan)
        text = re.sub(r'```(.*?)```', f'{cyan}\\1{reset}', text, flags=re.DOTALL)

        # 4. Inline code: `code` -> \033[36mcode\033[0m
        text = re.sub(r'`(.*?)`', f'{cyan}\\1{reset}', text)

        # 5. Hyperlinks: [text](url) -> text (url)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 (\2)', text)

        # 6. Headers: # Header -> BOLD Header
        text = re.sub(r'^(#{1,6})\s+(.*)$', f'{bold}\\2{reset}', text, flags=re.MULTILINE)

        # 7. Unordered Lists: * item or - item -> • item
        text = re.sub(r'^\s*[\*\-]\s+(.*)$', r'• \1', text, flags=re.MULTILINE)

        return text
