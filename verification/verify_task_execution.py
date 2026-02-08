import time
import threading
import queue
from datetime import datetime, timedelta
from agent_system.core.engine import Engine
from agent_system.core.scheduler import ScheduledTask
from utils.persistence import Persistence

# Mock Channel using a queue for output
class MockChannel:
    def __init__(self):
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()

    def send_output(self, text):
        self.output_queue.put(text)
        print(f"MOCK OUTPUT: {text}")

    def send_status(self, text):
        pass

    def show_activity(self, activity):
        pass

    def stop_activity(self):
        pass
    
    def get_input(self):
        return self.input_queue.get()

# Mock Provider
class MockProvider:
    def generate_response(self, messages, tools=None):
        last_msg = messages[-1]
        print(f"PROVIDER RECEIVED: {last_msg}")
        if last_msg["role"] == "user" and "Scheduled Task:" in last_msg["content"]:
            return "Task Received and Executed!"
        return "Silent"

def verify_scheduled_task():
    print("--- Verifying Scheduled Task ---")
    
    # Setup
    persistence = Persistence(sessions_dir="test_task_sessions", memory_dir="test_task_memory")
    channel = MockChannel()
    provider = MockProvider()
    
    # Initialize Engine
    engine = Engine(provider=provider, channels=[channel], persistence=persistence, workspace_dir="test_task_workspace")
    
    # Start engine in a thread
    engine_thread = threading.Thread(target=engine.run, daemon=True)
    engine_thread.start()
    
    # Wait for init
    time.sleep(1)
    
    # Create a task
    task = ScheduledTask("Test System Task", persistence.session_file, "at", datetime.now().astimezone().isoformat())
    
    # Inject task into engine's input queue (simulating scheduler callback)
    print("Injecting task...")
    engine._on_scheduled_task(task)
    
    # Wait for processing
    time.sleep(2)
    
    # Check output
    found_response = False
    while not channel.output_queue.empty():
        msg = channel.output_queue.get()
        if "Task Received and Executed!" in msg:
            found_response = True
        if "Scheduled Task Triggered" in msg:
            print("FAILURE: Task prompt was echoed to user channel!")
            return
            
    if found_response:
        print("SUCCESS: Model responded to task.")
    else:
        print("FAILURE: Model did not respond.")

    # Cleanup (simple exit)
    import shutil
    shutil.rmtree("test_task_sessions")
    shutil.rmtree("test_task_memory")
    shutil.rmtree("test_task_workspace")

if __name__ == "__main__":
    verify_scheduled_task()
