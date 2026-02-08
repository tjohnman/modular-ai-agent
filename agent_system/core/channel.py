from abc import ABC, abstractmethod
from typing import Union, Callable, Optional
from dataclasses import dataclass

@dataclass
class FileAttachment:
    """Represents a file attached to a message."""
    name: str
    content_getter: Callable[[], bytes]
    mime_type: Optional[str] = None
    caption: Optional[str] = None

class Channel(ABC):
    """Abstract base class for I/O channels."""
    
    @abstractmethod
    def get_input(self) -> Union[str, FileAttachment]:
        """Get input from the channel."""
        pass
    
    @abstractmethod
    def send_output(self, text: str):
        """Send output to the channel."""
        pass

    @abstractmethod
    def send_file(self, file_path: str, caption: Optional[str] = None):
        """Send a file to the channel."""
        pass
    
    @abstractmethod
    def show_activity(self, action: str = "typing"):
        """Shows that the assistant is performing an action."""
        pass

    @abstractmethod
    def send_status(self, text: str):
        """Sends a technical status update (may be suppressed by some channels)."""
        pass
