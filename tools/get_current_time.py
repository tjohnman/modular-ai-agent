from datetime import datetime

# The SCHEMA for the Google GenAI tool definition
SCHEMA = {
    "name": "get_current_time",
    "display_name": "Getting the time",
    "description": "Returns the current date and time.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

def execute(params: dict) -> str:
    """Executes the tool and returns the current time as a string."""
    now = datetime.now().astimezone()
    return f"The current date and time is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}."
