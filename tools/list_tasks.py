from agent_system.utils import logger

SCHEMA = {
    "name": "list_tasks",
    "description": "Lists all scheduled tasks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

def execute(args):
    try:
        scheduler = args.get("_scheduler")
        if not scheduler:
            return "Error: Scheduler instance not available in tool arguments."

        tasks = scheduler.list_tasks()
        if not tasks:
            return "No scheduled tasks found."

        output = "Scheduled Tasks:\n"
        for task in tasks:
            output += f"- ID: {task.id}\n"
            output += f"  Prompt: {task.prompt}\n"
            output += f"  Channel: {task.channel_name}\n"
            output += f"  Trigger: {task.trigger_type} = {task.trigger_value}\n"
            output += f"  Next Run: {task.next_run}\n"
            output += f"  Session: {task.session_file}\n"
            output += "-" * 20 + "\n"
        
        return output
            
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return f"Error listing tasks: {str(e)}"
