import threading
import time
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Callable
from croniter import croniter
from agent_system.utils import logger
from utils.persistence import Persistence

class ScheduledTask:
    def __init__(self, prompt: str, session_file: str, 
                 trigger_type: str, trigger_value: str, 
                 task_id: Optional[str] = None, created_at: Optional[str] = None,
                 next_run: Optional[str] = None):
        self.id = task_id or str(uuid.uuid4())
        self.prompt = prompt
        self.session_file = session_file
        self.trigger_type = trigger_type # 'at' or 'cron'
        self.trigger_value = trigger_value
        self.created_at = created_at or datetime.now().astimezone().isoformat()
        self.next_run = next_run
        
        if not self.next_run:
            self.calculate_next_run()

    def calculate_next_run(self):
        now = datetime.now().astimezone()
        if self.trigger_type == 'cron':
            try:
                iter = croniter(self.trigger_value, now)
                self.next_run = iter.get_next(datetime).isoformat()
            except Exception as e:
                logger.error(f"[Scheduler] Error calculating next run for cron '{self.trigger_value}': {e}")
                self.next_run = None
        elif self.trigger_type == 'at':
            # For 'at', the trigger_value IS the next run (if strictly ISO)
            # If it's relative like "in 5 mins", the tool should have converted it to ISO abs time.
            # We assume trigger_value is ISO format datetime string
            self.next_run = self.trigger_value

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "session_file": self.session_file,
            "trigger_type": self.trigger_type,
            "trigger_value": self.trigger_value,
            "created_at": self.created_at,
            "next_run": self.next_run
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ScheduledTask':
        return cls(
            prompt=data["prompt"],
            session_file=data["session_file"],
            trigger_type=data["trigger_type"],
            trigger_value=data["trigger_value"],
            task_id=data.get("id"),
            created_at=data.get("created_at"),
            next_run=data.get("next_run")
        )

class Scheduler:
    def __init__(self, persistence: Persistence, task_callback: Callable[[ScheduledTask], None]):
        self.persistence = persistence
        self.task_callback = task_callback
        self.tasks: List[ScheduledTask] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._load_tasks()

    def _load_tasks(self):
        tasks_data = self.persistence.load_scheduled_tasks()
        self.tasks = [ScheduledTask.from_dict(t) for t in tasks_data]
        logger.info(f"[Scheduler] Loaded {len(self.tasks)} scheduled tasks.")

    def _save_tasks(self):
        tasks_data = [t.to_dict() for t in self.tasks]
        self.persistence.save_scheduled_tasks(tasks_data)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("[Scheduler] Started background thread.")

    def stop(self):
        self.running = False
        # Do not join thread here as it might block if called from within the thread (though unlikely)
        # But for clean shutdown, we might want to wait a bit or just let daemon thread die.
        logger.info("[Scheduler] Stopped background thread signal sent.")

    def add_task(self, prompt: str, session_file: str, trigger_type: str, trigger_value: str) -> ScheduledTask:
        task = ScheduledTask(prompt, session_file, trigger_type, trigger_value)
        self.tasks.append(task)
        self._save_tasks()
        logger.info(f"[Scheduler] Added task {task.id}: {trigger_type}={trigger_value}, next_run={task.next_run}")
        return task

    def remove_task(self, task_id: str) -> bool:
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                del self.tasks[i]
                self._save_tasks()
                logger.info(f"[Scheduler] Removed task {task_id}")
                return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def list_tasks(self) -> List[ScheduledTask]:
        return self.tasks

    def _run_loop(self):
        logger.info("[Scheduler] Run loop started.")
        while self.running:
            try:
                self._check_and_run_tasks()
            except Exception as e:
                logger.error(f"[Scheduler] Error in loop: {e}")
            time.sleep(1) 

    def _check_and_run_tasks(self):
        now = datetime.now().astimezone()
        tasks_executed = False
        
        # Copy list to avoid modification during iteration if we remove
        for task in self.tasks[:]:
            if not task.next_run:
                continue
                
            try:
                next_run_dt = datetime.fromisoformat(task.next_run)
                # Ensure next_run_dt is aware if it wasn't already (backwards compatibility or just safety)
                if next_run_dt.tzinfo is None:
                     next_run_dt = next_run_dt.replace(tzinfo=now.tzinfo)
            except ValueError:
                logger.error(f"[Scheduler] Invalid next_run format for task {task.id}: {task.next_run}")
                continue

            if now >= next_run_dt:
                logger.info(f"[Scheduler] Triggering task {task.id} (due {task.next_run})")
                
                # Execute callback
                try:
                    self.task_callback(task)
                except Exception as e:
                    logger.error(f"[Scheduler] Error executing task callback: {e}")

                tasks_executed = True

                # Handle next iteration or removal
                if task.trigger_type == 'at':
                    # One-time task, remove it
                    self.tasks.remove(task)
                elif task.trigger_type == 'cron':
                    # Recurrent task, calculate next run
                    try:
                        iter = croniter(task.trigger_value, now)
                        task.next_run = iter.get_next(datetime).isoformat()
                        logger.info(f"[Scheduler] Rescheduled cron task {task.id} to {task.next_run}")
                    except Exception as e:
                        logger.error(f"[Scheduler] Error rescheduling cron task {task.id}: {e}")
                        # Remove if broken? Or keep trying? Let's keep it but next_run is invalid effectively?
                        # Probably safest to leave it or disable it.
                        pass
        
        if tasks_executed:
            self._save_tasks()
