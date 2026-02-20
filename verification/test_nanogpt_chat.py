import os
import sys
import json

import requests
from dotenv import load_dotenv

# Add the project root to sys.path to mirror app import behavior
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.config import load_config


def main() -> int:
    load_dotenv()
    api_key = os.getenv("NANOGPT_API_KEY", "")
    if not api_key:
        print("NANOGPT_API_KEY is not set.")
        return 1

    config = load_config()
    nano_cfg = config.get("nano_gpt", {})
    model = nano_cfg.get("model", "zai-org/glm-4.7")
    base_url = nano_cfg.get("base_url", "https://nano-gpt.com/api").rstrip("/")
    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with: OK"},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return 1

    print(f"status={resp.status_code}")
    try:
        data = resp.json()
    except Exception:
        print(resp.text[:2000])
        return 1

    if resp.status_code >= 400:
        err = data.get("error", {})
        message = err.get("message") or data
        print(f"error={message}")
        return 1

    message = data.get("choices", [{}])[0].get("message", {}).get("content")
    print("reply:", message)
    print("usage:", data.get("usage"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
