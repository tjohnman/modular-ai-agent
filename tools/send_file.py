import os
import shutil
import time

from agent_system.utils import logger

# The SCHEMA for the Google GenAI tool definition
SCHEMA = {
    "name": "send_file",
    "display_name": "Sending file",
    "description": "Queues a file from the workspace for delivery by placing it into the output pipeline.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Path to the file in the workspace (absolute or relative)."
            },
            "output_name": {
                "type": "STRING",
                "description": "Optional filename to use when placing the file into output."
            },
            "mode": {
                "type": "STRING",
                "enum": ["move", "copy"],
                "default": "move",
                "description": "Whether to move or copy the file into output."
            }
        },
        "required": ["file_path"]
    }
}


def _resolve_path(workspace_dir: str, file_path: str) -> str:
    if os.path.isabs(file_path):
        return os.path.abspath(file_path)
    return os.path.abspath(os.path.join(workspace_dir, file_path))


def execute(params: dict) -> str:
    file_path = params.get("file_path")
    output_name = params.get("output_name")
    mode = params.get("mode", "move")
    workspace_dir = params.get("_workspace")

    if not workspace_dir:
        return "Error: Workspace directory not found. Tool must be run via the Agent Engine."

    if not file_path:
        return "Error: file_path is required."

    resolved_path = _resolve_path(workspace_dir, file_path)
    workspace_dir = os.path.abspath(workspace_dir)

    if not resolved_path.startswith(workspace_dir + os.path.sep):
        return "Error: file_path must be inside the workspace."

    if not os.path.exists(resolved_path) or not os.path.isfile(resolved_path):
        return f"Error: File not found: {file_path}"

    output_dir = os.path.join(workspace_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    dest_name = output_name or os.path.basename(resolved_path)
    dest_path = os.path.join(output_dir, dest_name)

    if os.path.abspath(resolved_path) == os.path.abspath(dest_path):
        return f"File already queued for delivery: {dest_name}"

    if os.path.exists(dest_path):
        base, ext = os.path.splitext(dest_name)
        dest_name = f"{base}_{int(time.time())}{ext}"
        dest_path = os.path.join(output_dir, dest_name)

    try:
        if mode == "copy":
            shutil.copy2(resolved_path, dest_path)
        else:
            shutil.move(resolved_path, dest_path)
        logger.info(f"[Tool: send_file] Queued file for delivery: {dest_path}")
        return f"Queued file for delivery: {dest_name}"
    except Exception as e:
        error_msg = f"Error queueing file for delivery: {str(e)}"
        logger.error(f"[Tool: send_file] {error_msg}")
        return error_msg
