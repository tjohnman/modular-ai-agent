import time
import hashlib
import json
import os
from typing import List, Dict, Any, Optional
from agent_system.core.provider import Provider
from agent_system.utils import logger

try:
    from google import genai
    from google.genai import errors
except ImportError:
    genai = None
    errors = None

class GoogleProvider(Provider):
    """Implementation of Google Generative Language API provider."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-3-flash-preview"):
        self.api_key = api_key
        self.model_name = model_name
        self.last_usage: Dict[str, Any] = {
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "total_tokens": 0
        }
        if genai and self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
        
        self._cached_content: Optional[Any] = None
        self._cached_config_hash: Optional[str] = None
        self._cache_ttl_seconds: int = 3600 # 1 hour default

    def _make_serializable(self, obj: Any) -> Any:
        """Recursively converts bytes to base64 strings for JSON serialization."""
        import base64
        if isinstance(obj, bytes):
            return {"__bytes_b64__": base64.b64encode(obj).decode("utf-8")}
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._make_serializable(v) for v in obj]
        return obj

    def generate_response(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        if not self.client:
            return "[Error: google-genai package not installed or API key missing]"
        
        # Convert internal message format to Google's contents format
        contents = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue
            
            # Model response with tool call
            if role == "model" and "tool_call" in msg:
                tc = msg["tool_call"]
                model_part = {
                    "function_call": {
                        "name": tc["name"],
                        "args": tc["args"]
                    }
                }
                if tc.get("thought_signature"):
                    model_part["thought_signature"] = tc["thought_signature"]
                    
                contents.append({
                    "role": "model",
                    "parts": [model_part]
                })
                continue

            # Tool result
            if role == "tool" and "tool_result" in msg:
                contents.append({
                    "role": "user", # The SDK expects 'user' role for function responses in conversation history
                    "parts": [{
                        "function_response": {
                            "name": msg["name"],
                            "response": self._make_serializable(msg["tool_result"])
                        }
                    }]
                })
                continue

            # Standard message (possibly multimodal)
            role_map = {"user": "user", "assistant": "model", "model": "model"}
            mapped_role = role_map.get(role, "user")
            
            parts = []
            if "parts" in msg:
                for p in msg["parts"]:
                    if "text" in p:
                        parts.append({"text": p["text"]})
                    elif "file_path" in p:
                        fpath = p["file_path"]
                        try:
                            if os.path.exists(fpath):
                                with open(fpath, "rb") as f:
                                    file_bytes = f.read()
                                parts.append({
                                    "inline_data": {
                                        "mime_type": p["mime_type"],
                                        "data": file_bytes
                                    }
                                })
                            else:
                                logger.warning(f"[GoogleProvider] File not found: {fpath}")
                                parts.append({"text": f"[File Missing: {os.path.basename(fpath)}]"})
                        except Exception as e:
                            logger.error(f"[GoogleProvider] Error reading multimodal part {fpath}: {e}")
                            parts.append({"text": f"[Error reading file: {os.path.basename(fpath)}]"})
            else:
                parts.append({"text": msg["content"]})
                
            contents.append({"role": mapped_role, "parts": parts})
        
        # Find and combine all system messages
        system_messages = [msg["content"] for msg in messages if msg["role"] == "system"]
        system_instruction = "\n\n".join(system_messages) if system_messages else None

        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries + 1):
            try:
                # Get or create context cache
                cached_content = self._get_or_create_cache(system_instruction, tools)
                
                # Prepare config with tools if provided (if not using cache)
                config: Dict[str, Any] = {}
                if cached_content:
                    config["cached_content"] = cached_content.name
                else:
                    if system_instruction:
                        config["system_instruction"] = system_instruction
                    if tools:
                        config["tools"] = [{"function_declarations": tools}]

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config if config else None
                )
                
                # Store usage metadata
                if response.usage_metadata:
                    self.last_usage = {
                        "prompt_tokens": response.usage_metadata.prompt_token_count,
                        "candidates_tokens": response.usage_metadata.candidates_token_count,
                        "total_tokens": response.usage_metadata.total_token_count
                    }
                
                # Check for tool calls
                candidate = response.candidates[0]
                if candidate.content.parts[0].function_call:
                    part = candidate.content.parts[0]
                    fc = part.function_call
                    return {
                        "role": "model",
                        "tool_call": {
                            "name": fc.name,
                            "args": fc.args,
                            "thought_signature": getattr(part, "thought_signature", None)
                        }
                    }
                    
                return response.text
            except Exception as e:
                # Check for specific error types if needed, or handle general exceptions gracefully
                # If it's a ServerError, we retry. Otherwise, we might want to fail immediately.
                error_str = str(e)
                if "400" in error_str or "403" in error_str or "404" in error_str:
                     return f"[Error from Google Provider: {error_str}]"
                
                logger.error(f"[GoogleProvider] Attempt {attempt + 1} failed: {error_str}")
                if attempt < max_retries:
                    logger.info(f"[GoogleProvider] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    return f"[Error from Google Provider: All retries failed. Last error: {error_str}]"
        
        return "[Error from Google Provider: Unknown failure]"

    def get_usage(self) -> Dict[str, Any]:
        return self.last_usage

    def _get_or_create_cache(self, system_instruction: Optional[str], tools: Optional[List[Dict[str, Any]]]) -> Optional[Any]:
        """Manages explicit context caching for system instructions and tools."""
        if not self.client or not (system_instruction or tools):
            return None

        # Check if we should use caching (e.g. minimum token threshold)
        # For simplicity in this implementation, we always attempt to cache if content exists.
        # The API will handle the actual effectiveness.
        
        # Create a unique hash of the configuration to detect changes
        config_data = {
            "system_instruction": system_instruction,
            "tools": tools,
            "model": self.model_name
        }
        config_hash = hashlib.sha256(json.dumps(config_data, sort_keys=True).encode()).hexdigest()

        # If hash matches, return existing cache if it hasn't expired (simplified check)
        if self._cached_config_hash == config_hash and self._cached_content:
            try:
                # Try to get the cache to see if it still exists
                return self.client.caches.get(name=self._cached_content.name)
            except Exception:
                # If cache is gone/expired, proceed to recreate
                self._cached_content = None
        elif self._cached_config_hash != config_hash and self._cached_content:
            # Hash changed, old cache is no longer relevant for this configuration
            # We don't necessarily delete it here to avoid race conditions or if it's used elsewhere,
            # but we clear our reference.
            self._cached_content = None

        # Create new cache
        try:
            # Prepare parts for caching
            parts = []
            if system_instruction:
                parts.append({"text": system_instruction})
            
            # Tools need to be passed in the config when creating the cache in some SDK versions,
            # or as parts if they are represented as such. However, the standard way for 
            # Context Caching in Gemini is usually system_instruction + tools in the CACHE setup.
            
            cache_config: Dict[str, Any] = {}
            if system_instruction:
                cache_config["system_instruction"] = system_instruction
            if tools:
                cache_config["tools"] = [{"function_declarations": tools}]
            
            cache_config["ttl"] = f"{self._cache_ttl_seconds}s"

            # According to google-genai SDK docs, caches.create takes model and config.
            new_cache = self.client.caches.create(
                model=self.model_name,
                config=cache_config
            )
            
            self._cached_content = new_cache
            self._cached_config_hash = config_hash
            logger.info(f"[GoogleProvider] Created new context cache: {new_cache.name}")
            return new_cache
        except Exception as e:
            error_msg = str(e)
            if "400" in error_msg and "too small" in error_msg.lower():
                # Silently ignore "too small" errors and mark this hash as non-cacheable
                self._cached_config_hash = config_hash
                self._cached_content = None
            else:
                logger.error(f"[GoogleProvider] Failed to create cache: {e}")
            return None
