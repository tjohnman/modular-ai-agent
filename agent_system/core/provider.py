from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class Provider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """Generates a response from the LLM based on the provided messages."""
        ...

    @abstractmethod
    def get_usage(self) -> Dict[str, Any]:
        """Returns the usage metadata for the provider."""
        ...
