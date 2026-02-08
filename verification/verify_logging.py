import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from agent_system.utils import logger

def test_logging():
    print("--- Verification: Centralized Logging ---")
    
    # 1. Check if log directory exists
    log_dir = project_root / "log"
    if log_dir.exists():
        print(f"PASS: Log directory exists at {log_dir}")
    else:
        print(f"FAIL: Log directory does not exist!")
        return

    # 2. Emit some logs
    logger.info("Test INFO message")
    logger.warning("Test WARNING message")
    logger.error("Test ERROR message")
    logger.info("[Calling Tool: test_tool with {}]")
    logger.info("[File Sent: /path/to/test_file]")
    
    # 3. Check if log file contains the messages
    log_file = log_dir / "agent.log"
    if log_file.exists():
        with open(log_file, "r") as f:
            content = f.read()
            if "Test INFO message" in content and \
               "Test WARNING message" in content and \
               "Test ERROR message" in content and \
               "[Calling Tool: test_tool" in content and \
               "[File Sent: /path/to/test_file" in content:
                print(f"PASS: Log file contains expected messages (including tool and file reports).")
            else:
                print(f"FAIL: Log file is missing messages.")
                print("Content seen:")
                print(content)
    else:
        print(f"FAIL: Log file does not exist!")

if __name__ == "__main__":
    test_logging()
