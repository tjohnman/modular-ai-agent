import os
import sys

from dotenv import load_dotenv

# Add the project root to sys.path to mirror app import behavior
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def main() -> int:
    load_dotenv()
    key = os.getenv("NANOGPT_API_KEY", "")

    if not key:
        print("NANOGPT_API_KEY is not set.")
        return 1

    if not key.startswith("sk"):
        print("NANOGPT_API_KEY does not start with 'sk'.")
        return 1

    masked = f"{key[:2]}...{key[-4:]}" if len(key) >= 6 else "sk..."
    print(f"NANOGPT_API_KEY looks valid (masked: {masked}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
