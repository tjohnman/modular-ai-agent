import base64
import json
import time
from typing import List, Dict, Any, Optional

import requests

from agent_system.core.provider import Provider
from agent_system.providers.file_utils import read_file_bytes
from agent_system.utils import logger


class NanoGPTProvider(Provider):
    """Implementation of the NanoGPT OpenAI-compatible API provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        base_url: str = "https://nano-gpt.com/api",
        timeout_seconds: int = 60,
        debug_log_requests: bool = False,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.debug_log_requests = debug_log_requests
        self.last_usage: Dict[str, Any] = {
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "total_tokens": 0,
        }

    def _normalize_tool_schema(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Convert internal tool schema to OpenAI-compatible tool schema."""
        parameters = tool.get("parameters", {})
        normalized_params = self._normalize_json_schema(parameters)
        return {
            "type": "function",
            "function": {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "parameters": normalized_params,
            },
        }

    def _normalize_json_schema(self, schema: Any) -> Any:
        if isinstance(schema, dict):
            normalized = {}
            for key, value in schema.items():
                if key == "type" and isinstance(value, str):
                    normalized[key] = value.lower()
                else:
                    normalized[key] = self._normalize_json_schema(value)
            return normalized
        if isinstance(schema, list):
            return [self._normalize_json_schema(item) for item in schema]
        return schema

    def _serialize_tool_result(self, tool_result: Any) -> str:
        if isinstance(tool_result, str):
            return tool_result
        try:
            return json.dumps(tool_result, ensure_ascii=True)
        except Exception:
            return str(tool_result)

    def _build_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        openai_messages: List[Dict[str, Any]] = []
        pending_tool_calls: List[Dict[str, str]] = []
        call_index = 1

        for msg in messages:
            role = msg.get("role")
            if role == "system":
                openai_messages.append({"role": "system", "content": msg.get("content", "")})
                continue

            if role == "model" and "tool_call" in msg:
                tc = msg["tool_call"]
                call_id = tc.get("id") or f"call_{call_index}"
                call_index += 1
                pending_tool_calls.append({"id": call_id, "name": tc.get("name")})
                openai_messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tc.get("name"),
                            "arguments": json.dumps(tc.get("args", {}), ensure_ascii=True),
                        },
                    }],
                })
                continue

            if role == "tool" and "tool_result" in msg:
                tool_name = msg.get("name")
                tool_call_id = None
                for idx, pending in enumerate(pending_tool_calls):
                    if tool_name is None or pending["name"] == tool_name:
                        tool_call_id = pending["id"]
                        pending_tool_calls.pop(idx)
                        break
                if tool_call_id is None:
                    tool_call_id = f"call_{call_index}"
                    call_index += 1

                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": self._serialize_tool_result(msg.get("tool_result")),
                })
                continue

            mapped_role = "assistant" if role in ("assistant", "model") else "user"
            if "parts" in msg:
                content_parts = []
                for part in msg["parts"]:
                    if "text" in part:
                        content_parts.append({"type": "text", "text": part["text"]})
                    elif "file_path" in part:
                        file_bytes = read_file_bytes(part["file_path"])
                        if file_bytes is None:
                            content_parts.append({
                                "type": "text",
                                "text": f"[File Missing: {part.get('file_path', '')}]",
                            })
                            continue
                        mime_type = part.get("mime_type", "application/octet-stream")
                        if mime_type.startswith("image/"):
                            b64 = base64.b64encode(file_bytes).decode("ascii")
                            data_url = f"data:{mime_type};base64,{b64}"
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            })
                        else:
                            filename = part.get("file_path", "")
                            content_parts.append({
                                "type": "text",
                                "text": f"[File uploaded: {filename} ({mime_type})]",
                            })
                openai_messages.append({"role": mapped_role, "content": content_parts})
            else:
                openai_messages.append({"role": mapped_role, "content": msg.get("content", "")})

        return openai_messages

    def _build_request_debug(self, payload: Dict[str, Any]) -> str:
        messages = payload.get("messages", [])
        summary = []
        summary.append(f"model={payload.get('model')}")
        if "tools" in payload:
            tool_names = [t.get("function", {}).get("name") for t in payload.get("tools", [])]
            summary.append(f"tools={tool_names}")
        summary.append(f"tool_choice={payload.get('tool_choice')}")

        msg_summaries = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if isinstance(content, list):
                kinds = []
                for part in content:
                    kinds.append(part.get("type", "unknown"))
                msg_summaries.append(f"{role}:parts({','.join(kinds)})")
            else:
                text_len = len(content) if isinstance(content, str) else 0
                msg_summaries.append(f"{role}:text(len={text_len})")
        summary.append("messages=" + "; ".join(msg_summaries))
        return " | ".join(summary)

    def generate_response(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        if not self.api_key:
            return "[Error: NANOGPT_API_KEY is missing]"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/v1/chat/completions"

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": self._build_messages(messages),
        }

        if tools:
            payload["tools"] = [self._normalize_tool_schema(t) for t in tools]
            payload["tool_choice"] = "auto"

        max_retries = 3
        retry_delay = 3

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message") or response.text
                    except Exception:
                        error_msg = response.text

                    if self.debug_log_requests:
                        debug_info = self._build_request_debug(payload)
                        error_msg = f"{error_msg}\n\nRequest Debug:\n```text\n{debug_info}\n```"

                    if response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                        logger.warning(f"[NanoGPTProvider] Retryable error {response.status_code}: {error_msg}")
                        time.sleep(retry_delay)
                        continue

                    return f"[Error from NanoGPT Provider: {response.status_code} {error_msg}]"

                data = response.json()
                usage = data.get("usage", {})
                if usage:
                    self.last_usage = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "candidates_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }

                message = data.get("choices", [{}])[0].get("message", {})
                tool_calls = message.get("tool_calls") or []
                if tool_calls:
                    tc = tool_calls[0]
                    function = tc.get("function", {})
                    args_str = function.get("arguments", "{}")
                    try:
                        args = json.loads(args_str)
                    except Exception:
                        args = {"raw": args_str}

                    return {
                        "role": "model",
                        "tool_call": {
                            "name": function.get("name"),
                            "args": args,
                            "id": tc.get("id"),
                        },
                    }

                return message.get("content", "")
            except requests.RequestException as e:
                if attempt < max_retries:
                    logger.warning(f"[NanoGPTProvider] Request failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                return f"[Error from NanoGPT Provider: {str(e)}]"

        return "[Error from NanoGPT Provider: Unknown failure]"

    def get_usage(self) -> Dict[str, Any]:
        return self.last_usage
