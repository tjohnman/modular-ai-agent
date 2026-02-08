import os
import sys

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from unittest.mock import MagicMock
from agent_system.core.engine import Engine

def test_command_registry():
    provider = MagicMock()
    channel = MagicMock()
    persistence = MagicMock()
    
    # Mock file methods and Engine methods before instantiation
    os.path.exists = MagicMock(return_value=True)
    Engine._load_system_prompt = MagicMock(return_value="System Prompt")
    Engine.load_tools = MagicMock()
    Engine._ensure_dirs = MagicMock()
    
    engine = Engine(provider=provider, channels=[channel], persistence=persistence)
    
    print("Testing command registry...")
    assert "/help" in engine.commands
    assert "/usage" in engine.commands
    assert "/exit" in engine.commands
    assert "/reload" in engine.commands
    print("✓ Registry contains expected commands.")

    print("Testing /help output...")
    engine._handle_help()
    # Check if channel.send_output was called with help text
    args, kwargs = channel.send_output.call_args
    help_text = args[0]
    print(f"Help output received:\n{help_text}")
    assert "Available Slash Commands:" in help_text
    assert "/help" in help_text
    assert "/usage" in help_text
    print("✓ /help output looks correct.")

    print("Testing a future command...")
    # Simulate adding a new command
    engine.commands["/test"] = {
        "handler": lambda: True,
        "description": "A test command"
    }
    engine._handle_help()
    args, kwargs = channel.send_output.call_args
    help_text = args[0]
    assert "/test" in help_text
    print("✓ New commands are correctly reported in /help.")

if __name__ == "__main__":
    try:
        test_command_registry()
        print("\nALL TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
