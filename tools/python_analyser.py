import docker
import os
import textwrap

# The SCHEMA for the Google GenAI tool definition
SCHEMA = {
    "name": "python_analyser",
    "display_name": "Running Python code",
    "description": "Runs Python code in a sandboxed Docker container with file I/O support. Access files in '/workspace' and save outputs to '/workspace/output'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "code": {
                "type": "STRING",
                "description": "The Python code to execute. Use '/workspace' to access input files and '/workspace/output' for output files."
            },
            "packages": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "List of PyPI packages to install before execution (e.g., ['fonttools', 'brotli'])."
            },
            "system_packages": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "List of APT system packages to install before execution (e.g., ['libcairo2', 'libpango-1.0-0'])."
            },
            "input_files": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "List of input filenames provided by the user that should be available in /workspace."
            },
            "output_files": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "List of output filenames expected to be generated in /workspace/output."
            }
        },
        "required": ["code"]
    }
}

def execute(params: dict) -> str:
    """Executes the tool by running Python in a Docker container."""
    code = params.get("code")
    packages = params.get("packages", [])
    system_packages = params.get("system_packages", [])
    workspace_dir = params.get("_workspace") # Injected by the Engine
    
    if not workspace_dir:
        return "Error: Workspace directory not found. Tool must be run via the Agent Engine."

    client = docker.from_env()
    
    # To avoid shell escaping issues with heredocs, we write the code to a file in the workspace
    script_filename = "_exec_script.py"
    script_path = os.path.join(workspace_dir, script_filename)
    
    with open(script_path, "w") as f:
        f.write(code)

    # Prepare command components
    # 1. System packages (APT)
    apt_cmd = ""
    if system_packages:
        apt_cmd = f"apt-get update > /dev/null 2>&1 && apt-get install -y {' '.join(system_packages)} > /dev/null 2>&1 && "

    # 2. Python packages (PIP)
    pip_cmd = ""
    if packages:
        pip_cmd = f"pip install {' '.join(packages)} > /dev/null 2>&1 && "

    full_command = f"bash -c '{apt_cmd}{pip_cmd}python3 {script_filename}'"

    # Determine the host path for the volume
    # If we are running in a container, we must use the host's path (provided by the engine),
    # otherwise we use the local path.
    host_workspace_dir = params.get("_host_workspace", workspace_dir)

    try:
        output_bytes = client.containers.run(
            image="python:3.11", # Upgraded from slim to full
            command=full_command,
            volumes={host_workspace_dir: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            detach=False,
            remove=True,
            stderr=True,
            stdout=True
        )
        
        output = output_bytes.decode("utf-8")
        return f"Execution successful.\nOutput:\n{output}"
        
    except docker.errors.ContainerError as e:
        return f"Error during container execution:\n{e.stderr.decode('utf-8') if e.stderr else str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"
    finally:
        # Cleanup the temporary script file
        if os.path.exists(script_path):
            os.remove(script_path)
