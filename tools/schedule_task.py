from datetime import datetime, timedelta
from agent_system.utils import logger

SCHEMA = {
    "name": "schedule_task",
    "description": "Schedules a task to be executed at a specific time or recurrently.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "The prompt to execute."
            },
            "when": {
                "type": "STRING",
                "description": "When to execute. Format: ISO 8601 datetime (YYYY-MM-DDTHH:MM:SS) OR relative time like 'in 5 minutes', 'in 1 hour'. Used for one-time tasks."
            },
            "cron": {
                "type": "STRING",
                "description": "Cron expression for recurrent tasks. Use either 'when' or 'cron', not both."
            }
        },
        "required": ["prompt"]
    }
}

def execute(args):
    try:
        scheduler = args.get("_scheduler")
        if not scheduler:
            return "Error: Scheduler instance not available."
            
        prompt = args.get("prompt")
        when = args.get("when")
        cron = args.get("cron")
        channel_name = args.get("_channel_name", "terminal")
        
        # We need the current session file to associate the task with it.
        # But tools don't have access to persistence directly unless we inject it.
        # However, the scheduler is initialized with persistence.
        # The scheduler doesn't track "current" session of the engine.
        # But 'persistence' object in scheduler is the SAME instance as in Engine.
        # So scheduler.persistence.session_file IS the current session file.
        session_file = scheduler.persistence.session_file
        
        if cron:
            trigger_type = 'cron'
            trigger_value = cron
        elif when:
            trigger_type = 'at'
            # Simple parsing for MVP
            if when.lower().startswith("in "):
                # Parse relative "in X minutes/seconds/hours"
                parts = when.lower()[3:].strip().split()
                if len(parts) >= 2:
                    amount = int(parts[0])
                    unit = parts[1]
                    now = datetime.now()
                    if "minute" in unit:
                        dt = now + timedelta(minutes=amount)
                    elif "hour" in unit:
                        dt = now + timedelta(hours=amount)
                    elif "second" in unit:
                        dt = now + timedelta(seconds=amount)
                    elif "day" in unit:
                        dt = now + timedelta(days=amount)
                    else:
                        return f"Error: Unsupported time unit in '{when}'."
                    trigger_value = dt.isoformat()
                else:
                     return f"Error: Could not parse relative time '{when}'."
            else:
                # Assume ISO
                # Verify format
                try:
                    datetime.fromisoformat(when)
                    trigger_value = when
                except ValueError:
                    return f"Error: Invalid date format '{when}'. Use ISO 8601 or 'in X minutes'."
        else:
            return "Error: Must provide either 'when' or 'cron'."

        task = scheduler.add_task(prompt, session_file, trigger_type, trigger_value, channel_name=channel_name)
        
        return f"Task scheduled successfully. ID: {task.id}. Next run: {task.next_run}"

    except Exception as e:
        logger.error(f"Error scheduling task: {e}")
        return f"Error scheduling task: {str(e)}"
