from agent_system.utils import logger

SCHEMA = {
    "name": "delete_task",
    "description": "Deletes a scheduled task by its ID.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task_id": {
                "type": "STRING",
                "description": "The ID of the task to delete."
            }
        },
        "required": ["task_id"]
    }
}

def execute(args):
    try:
        task_id = args.get("task_id")
        
        # We need access to the scheduler instance.
        # Tools typically don't have access to the engine instance directly.
        # However, we can use the `persistence` to modify the file directly, 
        # BUT the running scheduler has the tasks in memory.
        # A restart would be needed if we only modify the file.
        # Ideally, we should have a way to communicate with the engine/scheduler.
        # Since tools are just functions, this is a limitation of the current architecture.
        # OPTION 1: The engine injects itself or the scheduler into the args (like _workspace).
        # OPTION 2: We modify the file and tell the user they might need to reload/restart?
        # OPTION 3: (Best) We update Engine.py to inject `_scheduler` into tool args.
        
        scheduler = args.get("_scheduler")
        if not scheduler:
            return "Error: Scheduler instance not available in tool arguments."

        if scheduler.remove_task(task_id):
            return f"Task {task_id} deleted successfully."
        else:
            return f"Task {task_id} not found."
            
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return f"Error deleting task: {str(e)}"
