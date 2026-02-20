import os
from typing import Optional

from agent_system.utils import logger


def read_file_bytes(file_path: str) -> Optional[bytes]:
    """Read a file as bytes, returning None on error."""
    if not os.path.exists(file_path):
        logger.warning(f"[Provider] File not found: {file_path}")
        return None

    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"[Provider] Error reading file {file_path}: {e}")
        return None
