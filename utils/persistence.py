import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
import base64

class Persistence:
    """Handles session persistence using JSONL files."""
    
    session_file: str

    def __init__(self, sessions_dir: str = "sessions", memory_dir: str = "memory"):
        self.sessions_dir = sessions_dir
        self.memory_dir = memory_dir
        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.memory_dir, exist_ok=True)
        
        latest = self._get_latest_session_file()
        if latest:
            self.session_file = latest
        else:
            self.start_new_session()

    def _get_latest_session_file(self) -> Optional[str]:
        """Finds the most recent session file in the sessions directory."""
        files = [f for f in os.listdir(self.sessions_dir) if f.endswith(".jsonl")]
        if not files:
            return None
        files.sort()
        return os.path.join(self.sessions_dir, files[-1])

    def start_new_session(self, title: Optional[str] = None):
        """Starts a new session file with the current timestamp and creates it."""
        import time
        # Ensure unique timestamp if called rapidly (e.g. in tests)
        time.sleep(0.1) 
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
        self.session_file = os.path.join(self.sessions_dir, f"{timestamp}.jsonl")
        # Ensure the file is created immediately
        with open(self.session_file, "w", encoding="utf-8") as f:
            pass
        if title:
            self.set_session_title(title)

    def _make_serializable(self, obj: Any) -> Any:
        """Recursively converts bytes to base64 strings."""
        if isinstance(obj, bytes):
            return {"__bytes_b64__": base64.b64encode(obj).decode("utf-8")}
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._make_serializable(v) for v in obj]
        return obj

    def save_message(self, role: str, content: str, name: Optional[str] = None, 
                     tool_call: Optional[Dict] = None, tool_result: Optional[Dict] = None,
                     parts: Optional[List[Dict[str, Any]]] = None):
        """Appends a message to the current session file with optional structural metadata and parts."""
        data: Dict[str, Any] = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        if name:
            data["name"] = name
        if tool_call:
            data["tool_call"] = tool_call
        if tool_result:
            data["tool_result"] = tool_result
        if parts:
            data["parts"] = parts
            
        serializable_data = self._make_serializable(data)
        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(serializable_data) + "\n")

    def set_session_title(self, title: str):
        """Sets the title for the current session by appending a metadata record."""
        data = {
            "type": "metadata",
            "key": "title",
            "value": title,
            "timestamp": datetime.now().isoformat()
        }
        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lists all sessions with their indices, creation times, and titles."""
        files = [f for f in os.listdir(self.sessions_dir) if f.endswith(".jsonl")]
        files.sort()
        
        sessions = []
        for i, filename in enumerate(files):
            path = os.path.join(self.sessions_dir, filename)
            title = None
            # Extract timestamp from filename
            # Filename format: YYYY-MM-DD_HH-MM-SS.jsonl
            timestamp_str = filename.replace(".jsonl", "").replace("_", " ")
            
            # Try to find the latest title in the file
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            if data.get("type") == "metadata" and data.get("key") == "title":
                                title = data.get("value")
                        except json.JSONDecodeError:
                            continue
            
            sessions.append({
                "index": i,
                "filename": filename,
                "timestamp": timestamp_str,
                "title": title or "Untitled Session"
            })
        return sessions

    def switch_session(self, index: int) -> bool:
        """Switches to a session by its index."""
        files = [f for f in os.listdir(self.sessions_dir) if f.endswith(".jsonl")]
        files.sort()
        
        if 0 <= index < len(files):
            self.session_file = os.path.join(self.sessions_dir, files[index])
            return True
        return False

    def has_title(self) -> bool:
        """Checks if the current session has a title metadata record."""
        if os.path.exists(self.session_file):
            with open(self.session_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "metadata" and data.get("key") == "title":
                            return True
                    except json.JSONDecodeError:
                        continue
        return False

    def _restore_serialized(self, obj: Any) -> Any:
        """Recursively restores base64 strings back to bytes."""
        if isinstance(obj, dict) and "__bytes_b64__" in obj:
            return base64.b64decode(obj["__bytes_b64__"])
        if isinstance(obj, dict):
            return {k: self._restore_serialized(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._restore_serialized(v) for v in obj]
        return obj

    def load_history(self) -> List[Dict[str, Any]]:
        """Loads message history from the current session file, including metadata and parts."""
        history = []
        if os.path.exists(self.session_file):
            with open(self.session_file, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    data = self._restore_serialized(data)
                    # Skip metadata records and other non-message types
                    if data.get("type") == "metadata" or "role" not in data:
                        continue
                        
                    msg: Dict[str, Any] = {"role": data["role"], "content": data["content"]}
                    if "name" in data:
                        msg["name"] = data["name"]
                    if "tool_call" in data:
                        msg["tool_call"] = data["tool_call"]
                    if "tool_result" in data:
                        msg["tool_result"] = data["tool_result"]
                    if "parts" in data:
                        msg["parts"] = data["parts"]
                    history.append(msg)
        return history

    def replace_history(self, messages: List[Dict[str, Any]]):
        """Overwrites the current session file with a new set of messages."""
        with open(self.session_file, "w", encoding="utf-8") as f:
            for msg in messages:
                msg["timestamp"] = datetime.now().isoformat()
                serializable_msg = self._make_serializable(msg)
                f.write(json.dumps(serializable_msg) + "\n")

    def save_scheduled_tasks(self, tasks: List[Dict[str, str]]):
        """Saves the scheduled tasks list to a JSON file."""
        tasks_file = os.path.join(self.memory_dir, "scheduled_tasks.json")
        with open(tasks_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)

    def load_scheduled_tasks(self) -> List[Dict[str, str]]:
        """Loads the scheduled tasks list from a JSON file."""
        tasks_file = os.path.join(self.memory_dir, "scheduled_tasks.json")
        if not os.path.exists(tasks_file):
            return []
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
