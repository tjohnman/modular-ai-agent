import os
import time
import threading
import re
import html
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Union, Optional, List, Dict, Any
from agent_system.core.channel import Channel, FileAttachment
from agent_system.utils import logger

class TelegramChannel(Channel):
    """Implementation of I/O via a Telegram Bot."""
    
    def __init__(self, token: Optional[str] = None, restricted_chat_id: Optional[str] = None):
        self.name = "telegram"
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.restricted_chat_id = restricted_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.active_activity: Optional[str] = None
        self.activity_thread: Optional[threading.Thread] = None
        self.stop_activity_event = threading.Event()
        
        # Configure robust session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be provided or set in environment variables.")
        
        logger.info(f"TelegramChannel initialized. Restricted to Chat ID: {self.restricted_chat_id}")

    def get_input(self) -> Union[str, FileAttachment]:
        """Polls for updates and returns user input."""
        while True:
            try:
                resp = self.session.get(f"{self.api_url}/getUpdates", params={"offset": self.offset, "timeout": 30}).json()
                if resp.get("ok") and resp.get("result"):
                    for update in resp["result"]:
                        self.offset = update["update_id"] + 1
                        
                        if "message" not in update:
                            continue
                            
                        message = update["message"]
                        chat_id = str(message["chat"]["id"])
                        
                        # Security check: restrict to user if configured
                        if self.restricted_chat_id and chat_id != str(self.restricted_chat_id):
                            continue
                            
                        # Handle text input
                        if "text" in message:
                            return message["text"]
                            
                        caption = message.get("caption")
                        
                        # Handle file attachments
                        if "document" in message:
                            return self._process_document(message["document"], caption=caption)
                        
                        if "photo" in message:
                            # Telegram sends multiple sizes, take the largest one
                            return self._process_photo(message["photo"][-1], caption=caption)

                        # Handle voice messages
                        if "voice" in message:
                            return self._process_voice(message["voice"], caption=caption)

                        # Handle audio files
                        if "audio" in message:
                            return self._process_audio(message["audio"], caption=caption)

                time.sleep(1) # Small delay to prevent tight loop if no updates
            except Exception as e:
                logger.error(f"Error getting input from Telegram: {e}")
                time.sleep(5)

    def _process_document(self, doc: Dict[str, Any], caption: Optional[str] = None) -> FileAttachment:
        file_id = doc["file_id"]
        filename = doc.get("file_name", "telegram_file")
        mime_type = doc.get("mime_type")
        
        def getter():
            file_resp = self.session.get(f"{self.api_url}/getFile", params={"file_id": file_id}).json()
            if file_resp.get("ok"):
                file_path = file_resp["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                return self.session.get(download_url).content
            return b""
            
        return FileAttachment(name=filename, content_getter=getter, mime_type=mime_type, caption=caption)

    def _process_photo(self, photo: Dict[str, Any], caption: Optional[str] = None) -> FileAttachment:
        file_id = photo["file_id"]
        filename = f"photo_{int(time.time())}.jpg"
        
        def getter():
            file_resp = self.session.get(f"{self.api_url}/getFile", params={"file_id": file_id}).json()
            if file_resp.get("ok"):
                file_path = file_resp["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                return self.session.get(download_url).content
            return b""
            
        return FileAttachment(name=filename, content_getter=getter, mime_type="image/jpeg", caption=caption)

    def _process_voice(self, voice: Dict[str, Any], caption: Optional[str] = None) -> FileAttachment:
        file_id = voice["file_id"]
        filename = f"voice_{int(time.time())}.ogg"
        mime_type = voice.get("mime_type", "audio/ogg")
        
        def getter():
            file_resp = self.session.get(f"{self.api_url}/getFile", params={"file_id": file_id}).json()
            if file_resp.get("ok"):
                file_path = file_resp["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                return self.session.get(download_url).content
            return b""
            
        return FileAttachment(name=filename, content_getter=getter, mime_type=mime_type, caption=caption)

    def _process_audio(self, audio: Dict[str, Any], caption: Optional[str] = None) -> FileAttachment:
        file_id = audio["file_id"]
        # Use provided file_name or generate one
        filename = audio.get("file_name", f"audio_{int(time.time())}.mp3")
        mime_type = audio.get("mime_type", "audio/mpeg")
        
        def getter():
            file_resp = self.session.get(f"{self.api_url}/getFile", params={"file_id": file_id}).json()
            if file_resp.get("ok"):
                file_path = file_resp["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                return self.session.get(download_url).content
            return b""
            
        return FileAttachment(name=filename, content_getter=getter, mime_type=mime_type, caption=caption)

    def send_output(self, text: str):
        """Sends a text message to the restricted chat ID, splitting long messages if needed."""
        self.stop_activity()
        if not self.restricted_chat_id:
            logger.warning("No restricted_chat_id set. Cannot send output.")
            return

        formatted_text = self._format_markdown(text)
        
        # Telegram's maximum message length is 4096 characters.
        MAX_LENGTH = 4000
        
        if len(formatted_text) <= MAX_LENGTH:
            messages = [formatted_text]
        else:
            messages = self._split_message(formatted_text, MAX_LENGTH)

        for msg in messages:
            try:
                payload = {
                    "chat_id": self.restricted_chat_id,
                    "text": msg,
                    "parse_mode": "HTML"
                }
                resp = self.session.post(f"{self.api_url}/sendMessage", json=payload)
                resp.raise_for_status()
                
                result = resp.json()
                if not result.get("ok"):
                    logger.error(f"Telegram API error (sendMessage): {result.get('description')}")
            except Exception as e:
                logger.error(f"Error sending message to Telegram: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        logger.error(f"Telegram Response: {e.response.json()}")
                    except:
                        logger.error(f"Telegram Response Text: {e.response.text}")

    def _split_message(self, text: str, max_length: int) -> List[str]:
        """Splits message into chunks, ensuring HTML tags are balanced across chunks."""
        chunks = []
        current_pos = 0
        total_len = len(text)
        active_tags = [] # Format: [(tag, href), ...]
        
        while current_pos < total_len:
            # Prefix for this chunk: re-open tags from previous chunk
            prefix = ""
            for tag, href in active_tags:
                if tag == 'a' and href:
                    prefix += f'<a href="{href}">'
                else:
                    prefix += f"<{tag}>"
            
            # Suffix for this chunk: close tags currently active
            suffix = ""
            for tag, _ in reversed(active_tags):
                suffix += f"</{tag}>"
            
            # Target length for NEW content in this chunk
            # available = max_length - prefix - suffix
            chunk_max_content = max_length - len(prefix) - len(suffix)
            if chunk_max_content < 500 and total_len - current_pos > 500:
                # If prefix/suffix are too long, ensure we at least make progress
                # 4000 is slightly below the 4096 absolute limit
                chunk_max_content = 500
            
            # Look for split point in text[current_pos : current_pos + chunk_max_content]
            split_limit = min(current_pos + chunk_max_content, total_len)
            split_at = split_limit
            
            if split_at < total_len:
                # Try to find a good split point (newline or space)
                newline_pos = text.rfind('\n', current_pos, split_at)
                if newline_pos != -1 and newline_pos > current_pos + (chunk_max_content // 2):
                    split_at = newline_pos + 1
                else:
                    space_pos = text.rfind(' ', current_pos, split_at)
                    if space_pos != -1 and space_pos > current_pos + (chunk_max_content // 2):
                        split_at = space_pos + 1
            
            raw_content = text[current_pos : split_at]
            
            # Update active_tags based on tags found in this raw_content
            # Group 1: is_closing, Group 2: tag_name, Group 3: href_content
            tag_regex = re.compile(r'<(/?)(b|i|u|s|code|pre|a)(?:\s+href="([^"]*)")?>')
            for match in tag_regex.finditer(raw_content):
                is_closing = match.group(1) == '/'
                tag_name = match.group(2)
                href = match.group(3)
                if is_closing:
                    if active_tags and active_tags[-1][0] == tag_name:
                        active_tags.pop()
                else:
                    active_tags.append((tag_name, href))
            
            # Re-calculate suffix for the ACTUAL content (it might have balanced some tags)
            actual_suffix = ""
            for tag, _ in reversed(active_tags):
                actual_suffix += f"</{tag}>"
                
            chunks.append(prefix + raw_content + actual_suffix)
            current_pos = split_at
            
        return chunks

    def send_file(self, file_path: str, caption: Optional[str] = None):
        """Sends a file to the restricted chat ID."""
        self.stop_activity()
        if not self.restricted_chat_id:
            logger.warning("No restricted_chat_id set. Cannot send file.")
            return

        try:
            filename = os.path.basename(file_path)
            # Decide whether to use sendDocument or sendPhoto based on extension
            is_photo = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
            is_voice = filename.lower().endswith(('.wav', '.ogg', '.mp3', '.m4a'))
            
            if is_photo:
                method = "sendPhoto"
                file_key = "photo"
            elif is_voice:
                method = "sendVoice"
                file_key = "voice"
            else:
                method = "sendDocument"
                file_key = "document"

            with open(file_path, "rb") as f:
                files = {file_key: (filename, f)}
                data = {"chat_id": self.restricted_chat_id}
                if caption:
                    # Strip headers and complex MD from captions as they are more restrictive
                    formatted_caption = self._format_markdown(caption)
                    data["caption"] = formatted_caption
                    data["parse_mode"] = "HTML"
                resp = self.session.post(f"{self.api_url}/{method}", data=data, files=files)
                resp.raise_for_status()
                
                result = resp.json()
                if not result.get("ok"):
                    logger.error(f"Telegram API error ({method}): {result.get('description')}")
        except Exception as e:
            logger.error(f"Error sending file to Telegram: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    logger.error(f"Telegram Response: {e.response.json()}")
                except:
                    pass

    def show_activity(self, action: str = "typing"):
        """Shows a periodic chat action in Telegram until stopped."""
        if not self.restricted_chat_id:
            return

        if self.active_activity == action:
            return

        self.stop_activity()
        self.active_activity = action
        self.stop_activity_event.clear()
        self.activity_thread = threading.Thread(target=self._activity_loop, args=(action,), daemon=True)
        self.activity_thread.start()

    def stop_activity(self):
        """Stops the current chat action."""
        if self.active_activity:
            self.stop_activity_event.set()
            if self.activity_thread and self.activity_thread.is_alive():
                # Wait briefly for the thread to exit to avoid overlapping threads
                self.activity_thread.join(timeout=1.0)
            self.active_activity = None
            self.activity_thread = None

    def _activity_loop(self, action: str):
        """Sends chat action periodically."""
        while not self.stop_activity_event.is_set():
            try:
                payload = {
                    "chat_id": self.restricted_chat_id,
                    "action": action
                }
                resp = self.session.post(f"{self.api_url}/sendChatAction", json=payload)
                resp.raise_for_status()
                # Telegram chat actions expire after ~5 seconds
                self.stop_activity_event.wait(4)
            except Exception as e:
                # Log but continue the loop unless it's a persistent failure
                logger.debug(f"Error sending periodic chat action to Telegram: {e}")
                self.stop_activity_event.wait(2)

    def send_status(self, text: str):
        """Telegram suppresses technical status updates to avoid chat clutter."""
        pass

    def set_commands(self, commands: dict):
        """Registers slash commands with Telegram via setMyCommands API."""
        tg_commands = []
        for cmd, info in commands.items():
            # Telegram commands must not start with / for setMyCommands
            # and must only contain lowercase English letters, digits and underscores.
            cmd_text = cmd.lstrip("/").lower()
            if not re.match(r'^[a-z0-9_]+$', cmd_text):
                continue
                
            tg_commands.append({
                "command": cmd_text,
                "description": info.get("description", "No description")
            })
            
        if not tg_commands:
            return

        try:
            resp = self.session.post(f"{self.api_url}/setMyCommands", json={"commands": tg_commands})
            resp.raise_for_status()
            if resp.json().get("ok"):
                logger.info(f"[Telegram] Successfully registered {len(tg_commands)} commands.")
            else:
                logger.error(f"[Telegram] Failed to register commands: {resp.json().get('description')}")
        except Exception as e:
            logger.error(f"[Telegram] Error calling setMyCommands: {e}")

    def _format_markdown(self, text: str) -> str:
        """Converts basic Markdown to Telegram-compatible HTML, avoiding interleaved tags."""
        
        # 1. Handle code blocks and inline code FIRST using opaque placeholders
        # This protects their content from being escaped or modified by other rules
        placeholders = []
        
        def save_placeholder(tag, content):
            idx = len(placeholders)
            # Use unique tokens that won't be matched by bold/italic regex (no * or _)
            placeholder = f"§{tag}{idx}§"
            # Escape HTML inside code
            escaped_content = html.escape(content)
            if tag == "pre":
                placeholders.append(f"<pre>{escaped_content}</pre>")
            else:
                placeholders.append(f"<code>{escaped_content}</code>")
            return placeholder

        # Multi-line code blocks
        text = re.sub(r'```(.*?)```', lambda m: save_placeholder("pre", m.group(1)), text, flags=re.DOTALL)
        # Inline code
        text = re.sub(r'`(.*?)`', lambda m: save_placeholder("code", m.group(1)), text)
        
        # 2. Protect URLs in Markdown links before escaping or formatting
        # This prevents underscores in URLs from being turned into <i> tags
        def save_url_placeholder(match):
            idx = len(placeholders)
            placeholder = f"§url{idx}§"
            placeholders.append(match.group(2))
            return f"[{match.group(1)}]({placeholder})"
            
        text = re.sub(r'\[(.*?)\]\((.*?)\)', save_url_placeholder, text)

        # 3. Escape HTML special characters for the rest of the text
        text = html.escape(text)

        # 4. Handle Headers (convert to bold)
        def clean_header(match):
            content = match.group(2)
            # Remove MD formatting from headers to prevent nesting complications
            content = re.sub(r'[\*_]', '', content)
            return f"<b>{content}</b>"
            
        text = re.sub(r'^(#{1,6})\s+(.*)$', clean_header, text, flags=re.MULTILINE)

        # 5. Bold: **text** or __text__ -> <b>text</b>
        # Require that the first/last characters are not whitespace or the symbol itself 
        # to prevent triple-symbol interleaving (e.g., ***triple*** matching ** then *)
        text = re.sub(r'\*\*([^\s\*](?:.*?[^\s\*])?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\_\_([^\s\_](?:.*?[^\s\_])?)\_\_', r'<b>\1</b>', text)

        # 6. Italic: *text* or _text_ -> <i>text</i>
        text = re.sub(r'(?<!\*)\*([^\s\*](?:.*?[^\s\*])?)\*(?!\*)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!\_)\_([^\s\_](?:.*?[^\s\_])?)\_(?!\_)', r'<i>\1</i>', text)

        # 7. Finalize Hyperlinks: [text](PLACEHOLDER) -> <a href="original_url">text</a>
        # This converts the protected link structure to final HTML
        def restore_link(match):
            text_part = match.group(1)
            placeholder = match.group(2)
            # Find the original URL from placeholders
            match_p = re.match(r'§url(\d+)§', placeholder)
            if match_p:
                url = placeholders[int(match_p.group(1))]
                return f'<a href="{url}">{text_part}</a>'
            return match.group(0) # Should not happen

        text = re.sub(r'\[(.*?)\]\((§url\d+§)\)', restore_link, text)

        # 8. Unordered Lists: * item or - item -> • item
        text = re.sub(r'^\s*[\*\-]\s+(.*)$', r'• \1', text, flags=re.MULTILINE)

        # 9. Restore Code/Pre placeholders
        for i, val in enumerate(placeholders):
            # Only restore pre/code; URLs are handled in step 7
            text = text.replace(f"§pre{i}§", val).replace(f"§code{i}§", val)

        return text
