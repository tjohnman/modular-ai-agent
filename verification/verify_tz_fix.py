from datetime import datetime
from agent_system.core.scheduler import Scheduler, ScheduledTask
from utils.persistence import Persistence
import time
import os
import shutil

# Mock callback
def on_task(task):
    print(f"TASK TRIGGERED: {task.prompt} at {datetime.now().astimezone()}")

def test_manual():
    print("--- Manual Verification ---")
    test_dir = "test_manual_sessions"
    test_memory = "test_manual_memory"
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(test_memory, exist_ok=True)
    
    persistence = Persistence(sessions_dir=test_dir, memory_dir=test_memory)
    scheduler = Scheduler(persistence, on_task)
    scheduler.start()
    
    now = datetime.now().astimezone()
    print(f"Current System Time: {now}")
    print(f"Timezone: {now.tzinfo}")
    
    # helper to print tool output
    from tools import get_current_time
    print(f"Tool Output: {get_current_time.execute({})}")

    scheduler.stop()
    shutil.rmtree(test_dir)
    shutil.rmtree(test_memory)

if __name__ == "__main__":
    test_manual()
