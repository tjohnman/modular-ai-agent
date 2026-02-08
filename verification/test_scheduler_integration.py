import unittest
import time
import os
import shutil
import json
from datetime import datetime, timedelta
from agent_system.core.scheduler import Scheduler, ScheduledTask
from utils.persistence import Persistence

class TestSchedulerIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_sessions"
        self.test_memory_dir = "test_memory"
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.test_memory_dir, exist_ok=True)
        self.persistence = Persistence(sessions_dir=self.test_dir, memory_dir=self.test_memory_dir)
        self.triggered_tasks = []

    def tearDown(self):
        if hasattr(self, 'scheduler') and self.scheduler.running:
            self.scheduler.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if os.path.exists(self.test_memory_dir):
            shutil.rmtree(self.test_memory_dir)

    def on_task_trigger(self, task):
        self.triggered_tasks.append(task)

    def test_schedule_one_time_task(self):
        self.scheduler = Scheduler(self.persistence, self.on_task_trigger)
        self.scheduler.start()

        # Schedule task for 2 seconds in the future
        run_time = (datetime.now().astimezone() + timedelta(seconds=2)).isoformat()
        task = self.scheduler.add_task("Test Prompt", "session_1.jsonl", "at", run_time)
        
        print(f"Task scheduled at {run_time}")
        
        # Wait for 3 seconds
        time.sleep(4)
        
        self.assertEqual(len(self.triggered_tasks), 1)
        self.assertEqual(self.triggered_tasks[0].id, task.id)
        self.assertEqual(self.triggered_tasks[0].prompt, "Test Prompt")
        
        # Check if task is removed from scheduler
        self.assertEqual(len(self.scheduler.tasks), 0)

    def test_persistence_of_tasks(self):
        self.scheduler = Scheduler(self.persistence, self.on_task_trigger)
        
        # Add a future task
        future_time = (datetime.now().astimezone() + timedelta(hours=1)).isoformat()
        task = self.scheduler.add_task("Future Task", "session_1.jsonl", "at", future_time)
        
        # Restart scheduler
        self.scheduler = Scheduler(self.persistence, self.on_task_trigger)
        
        self.assertEqual(len(self.scheduler.tasks), 1)
        self.assertEqual(self.scheduler.tasks[0].id, task.id)
        self.assertEqual(self.scheduler.tasks[0].trigger_type, "at")

    def test_list_and_remove_task(self):
        self.scheduler = Scheduler(self.persistence, self.on_task_trigger)
        
        task1 = self.scheduler.add_task("Task 1", "s1", "at", datetime.now().astimezone().isoformat())
        task2 = self.scheduler.add_task("Task 2", "s2", "at", datetime.now().astimezone().isoformat())
        
        tasks = self.scheduler.list_tasks()
        self.assertEqual(len(tasks), 2)
        
        self.scheduler.remove_task(task1.id)
        tasks = self.scheduler.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, task2.id)

if __name__ == "__main__":
    unittest.main()
