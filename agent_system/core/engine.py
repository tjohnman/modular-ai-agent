import os
import importlib.util
import shutil
import queue
import threading
from typing import List, Dict, Any, Union, Optional
from agent_system.core.provider import Provider
from agent_system.core.channel import Channel, FileAttachment
from agent_system.core.scheduler import Scheduler, ScheduledTask
from utils.persistence import Persistence
from agent_system.utils import logger

class Engine:
    """The central loop coordinating channels, providers, and persistence."""
    
    def __init__(self, provider: Provider, channels: Union[Channel, List[Channel]], persistence: Persistence, 
                 system_prompt_path: str = "memory/SYSTEM.md", tools_dir: str = "tools", 
                 workspace_dir: str = "workspace", context_compact_threshold: Optional[int] = None):
        self.provider = provider
        # Ensure channels is a list
        self.channels = channels if isinstance(channels, list) else [channels]
        self.persistence = persistence
        self.system_prompt_path = system_prompt_path
        self.tools_dir = tools_dir
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.host_workspace_dir = os.getenv("WORKSPACE_HOST_PATH")
        self.context_compact_threshold = context_compact_threshold
        self.system_prompt = self._load_system_prompt(self.system_prompt_path)
        self.tools = {}
        self.commands = {}
        
        # Multi-channel support
        self.input_queue = queue.Queue()
        self.current_channel = self.channels[0] # Default to first channel
        
        # Scheduler
        self.scheduler = Scheduler(self.persistence, self._on_scheduled_task)
        
        self._ensure_dirs()
        self.load_tools()
        self._register_commands()

    def _ensure_dirs(self):
        """Ensures that required directories exist."""
        for d in [self.tools_dir, self.workspace_dir]:
            if not os.path.exists(d):
                os.makedirs(d)
        
        # Ensure output dir inside workspace exists
        output_dir = os.path.join(self.workspace_dir, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def load_tools(self):
        """Dynamically loads tools from the tools directory."""
        self.tools = {}
        for filename in os.listdir(self.tools_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                file_path = os.path.join(self.tools_dir, filename)
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is not None:
                        module = importlib.util.module_from_spec(spec)
                        if spec.loader:
                            spec.loader.exec_module(module)
                        
                        if hasattr(module, "SCHEMA") and hasattr(module, "execute"):
                            # Extract display_name for user feedback, but keep SCHEMA clean for the API
                            schema = module.SCHEMA.copy()
                            display_name = schema.pop("display_name", schema["name"])
                            
                            self.tools[module.SCHEMA["name"]] = {
                                "schema": schema,
                                "display_name": display_name,
                                "execute": module.execute
                            }
                            logger.info(f"[Engine] Loaded tool: {module.SCHEMA['name']}")
                except Exception as e:
                    logger.error(f"[Engine] Failed to load tool {module_name}: {str(e)}")

    def _load_system_prompt(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "You are a helpful assistant."

    def _register_commands(self):
        """Registers built-in slash commands."""
        self.commands = {
            "/help": {
                "handler": self._handle_help,
                "description": "Show this help message"
            },
            "/usage": {
                "handler": self._handle_usage,
                "description": "Show token usage for the current provider"
            },
            "/compact": {
                "handler": self._handle_compact,
                "description": "Compact conversation history into a summary"
            },
            "/clear": {
                "handler": self._handle_clear,
                "description": "Clear conversation history and start a new session"
            },
            "/reset": {
                "handler": self._handle_reset,
                "description": "Start a new session and completely empty the workspace"
            },
            "/reload": {
                "handler": self._handle_reload,
                "description": "Reload system prompt and dynamic tools"
            },
            "/new": {
                "handler": self._handle_new,
                "description": "Start a new session (usage: /new [title])"
            },
            "/list": {
                "handler": self._handle_list,
                "description": "List all sessions"
            },
            "/switch": {
                "handler": self._handle_switch,
                "description": "Switch to a session (usage: /switch <index>)"
            },
            "/name": {
                "handler": self._handle_name,
                "description": "Name the current session (usage: /name <title>)"
            },
            "/exit": {
                "handler": self._handle_exit,
                "description": "Exit the session"
            },
            "/quit": {
                "handler": self._handle_exit,
                "description": "Exit the session (alias for /exit)"
            }
        }

    def _handle_help(self):
        help_text = "Available Slash Commands:\n"
        for cmd, info in sorted(self.commands.items()):
            help_text += f"  {cmd.ljust(10)} - {info['description']}\n"
        self.current_channel.send_output(help_text)
        return True

    def _handle_usage(self):
        usage = self.provider.get_usage()
        output = (
            f"Usage Data:\n"
            f"- Prompt Tokens: {usage.get('prompt_tokens', 0)}\n"
            f"- Candidates Tokens: {usage.get('candidates_tokens', 0)}\n"
            f"- Total Tokens: {usage.get('total_tokens', 0)}"
        )
        self.current_channel.send_output(output)
        return True

    def _handle_compact(self):
        self.current_channel.send_status("Compacting context... please wait.")
        history = self.persistence.load_history()
        if len(history) <= 6:
            self.current_channel.send_output("Not enough history to compact (less than 6 turns).")
            return True
        
        history_to_summarize = history[:-6]
        history_to_keep = history[-6:]
        
        summary_prompt = (
            "Please provide a concise summary of our conversation so far, capturing all important details and context. "
            "This summary will replace the earlier part of our history to save space. "
            "Make sure to include any important facts, decisions, or user preferences mentioned. "
            "Begin the summary immediately without any preamble."
        )
        
        # We include the system prompt to give context to the summarizer
        temp_messages = [{"role": "system", "content": self.system_prompt}] + history_to_summarize + [{"role": "user", "content": summary_prompt}]
        summary = self.provider.generate_response(temp_messages)
        
        new_history = [
            {"role": "system", "content": f"Summary of previous conversation:\n{summary}"},
            {"role": "system", "content": "The previous conversation history has been compacted to save space. The summary above captures the key points. The most recent turns follow."}
        ]
        new_history.extend(history_to_keep)
        
        self.persistence.replace_history(new_history)
        self.current_channel.send_output(f"Context compacted. Preserved the last 6 turns.")
        return True

    def _handle_clear(self):
        self.persistence.start_new_session()
        self.current_channel.send_output("Context cleared. Started a new session file.")
        return True

    def _handle_reset(self):
        self.persistence.start_new_session()
        # Empty workspace
        for item in os.listdir(self.workspace_dir):
            item_path = os.path.join(self.workspace_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                logger.error(f"[Engine] Failed to delete {item_path}: {e}")
        
        # Re-ensure workspace structure (especially the 'output' folder)
        self._ensure_dirs()
        
        self.current_channel.send_output("Session reset. Conversation history cleared and workspace emptied.")
        return True

    def _handle_reload(self):
        self.system_prompt = self._load_system_prompt(self.system_prompt_path)
        self.load_tools()
        self.current_channel.send_output(f"System prompt and tools reloaded ({len(self.tools)} tools loaded).")
        return True

    def _handle_new(self, title: Optional[str] = None):
        self.persistence.start_new_session(title=title)
        msg = "Started a new session."
        if title:
            msg += f" Titled: {title}"
        self.current_channel.send_output(msg)
        return True

    def _handle_list(self):
        sessions = self.persistence.list_sessions()
        if not sessions:
            self.current_channel.send_output("No sessions found.")
            return True
        
        output = "Available Sessions:\n"
        for s in sessions:
            output += f"  [{s['index']}] {s['timestamp']} - {s['title']}\n"
        self.current_channel.send_output(output)
        return True

    def _handle_switch(self, index_str: Optional[str] = None):
        if index_str is None:
            self.current_channel.send_output("Usage: /switch <index>. Use /list to see indices.")
            return True
        
        try:
            index = int(index_str)
            if self.persistence.switch_session(index):
                self.current_channel.send_output(f"Switched to session [{index}]. Loaded history.")
            else:
                self.current_channel.send_output(f"Invalid session index: {index}")
        except ValueError:
            self.current_channel.send_output("Index must be a number.")
        return True

    def _handle_name(self, title: Optional[str] = None):
        if not title:
            self.current_channel.send_output("Usage: /name <title>")
            return True
        
        self.persistence.set_session_title(title)
        self.current_channel.send_output(f"Session titled: {title}")
        return True

    def _handle_exit(self):
        self.current_channel.send_output("Goodbye!")
        return False # Returning False signals the loop to break

    def _poll_channel(self, channel: Channel):
        """Polls a single channel for input and puts it in the shared queue."""
        while True:
            try:
                user_input = channel.get_input()
                self.input_queue.put((channel, user_input))
            except Exception as e:
                logger.error(f"[Engine] Error polling channel: {e}")
                break

    def _on_scheduled_task(self, task: ScheduledTask):
        """Callback for when a scheduled task is triggered."""
        # Find the correct channel
        target_channel = self.channels[0]
        for ch in self.channels:
            if getattr(ch, "name", "terminal") == task.channel_name:
                target_channel = ch
                break
        
        # Use the target channel for routing to the loop
        self.input_queue.put((target_channel, task))

    def run(self):
        """Starts the conversation loop with multi-channel support."""
        for channel in self.channels:
            channel.set_commands(self.commands)
            channel.send_output("AI Agent System initialized. Type '/exit' or '/quit' to end the session.")
            # Start a thread for each channel's get_input
            thread = threading.Thread(target=self._poll_channel, args=(channel,), daemon=True)
            thread.start()
        
        # Start Scheduler
        self.scheduler.start()
        
        try:
            while True:
                # Wait for input from ANY channel
                self.current_channel, user_input = self.input_queue.get()
                
                # Handle File Attachments
                if isinstance(user_input, FileAttachment):
                    self.current_channel.show_activity("upload_document")
                    file_path = os.path.join(self.workspace_dir, user_input.name)
                    with open(file_path, "wb") as f:
                        f.write(user_input.content_getter())
                    
                    parts = [{"file_path": file_path, "mime_type": user_input.mime_type}]
                    if user_input.caption:
                        parts.insert(0, {"text": user_input.caption})
                    
                    # Save as a multimodal user message
                    self.persistence.save_message("user", user_input.caption or f"[Uploaded {user_input.name}]", parts=parts)
                    
                    is_audio = user_input.mime_type and user_input.mime_type.startswith("audio/")
                    is_image = user_input.mime_type and user_input.mime_type.startswith("image/")
                    
                    if is_audio or is_image or user_input.caption:
                        logger.info(f"[Engine] Media/Captioned File Received (Stored as Parts): {user_input.name}")
                        # Proceed to model turn
                    else:
                        logger.info(f"[Engine] File Received and Saved: {user_input.name}")
                        # Keep system message for non-multimodal/non-captioned files just as a record
                        self.persistence.save_message("system", f"SYSTEM: User uploaded file '{user_input.name}'. It has been saved to the workspace.")
                        continue

                # Handle Scheduled Tasks
                if isinstance(user_input, ScheduledTask):
                    # Switch session if needed
                    if self.persistence.session_file != user_input.session_file:
                        sessions = self.persistence.list_sessions()
                        target_index = -1
                        target_filename = os.path.basename(user_input.session_file)
                        for s in sessions:
                            if s["filename"] == target_filename:
                                target_index = s["index"]
                                break
                        
                        if target_index != -1:
                            self.persistence.switch_session(target_index)
                            self.current_channel.send_output(f"Switched to session [{target_index}] for task.")
                        else:
                            self.persistence.start_new_session() # Fallback to new session if not found? Or just stay?
                            # Staying is prob safer, but let's log it.
                            logger.warning(f"[Engine] Could not find session {user_input.session_file} for task. Staying in current session.")

                    # Save as USER message but do not echo it.
                    # We use 'user' role because the model is trained to respond to user messages.
                    # System messages at the end of the conversation are sometimes ignored or treated as status updates.
                    user_msg = f"Scheduled Task: {user_input.prompt}"
                    self.persistence.save_message("user", user_msg)
                    
                    # Set user_input to None to bypass slash commands and user message saving
                    # ensuring we fall through to the generation loop immediately
                    user_input = None


                # Handle Slash Commands
                if isinstance(user_input, str) and user_input.startswith("/"):
                    parts = user_input.split(" ", 1)
                    command = parts[0].lower().strip()
                    args = parts[1] if len(parts) > 1 else None
                    
                    if command in self.commands:
                        handler = self.commands[command]["handler"]
                        # Check if handler accepts arguments
                        import inspect
                        sig = inspect.signature(handler)
                        if len(sig.parameters) > 0:
                            should_continue = handler(args)
                        else:
                            should_continue = handler()
                            
                        if not should_continue:
                            break
                        continue
                    else:
                        self.current_channel.send_output(f"Unknown command: {command}. Type /help for available commands.")
                        continue
                
                # Save user input
                if isinstance(user_input, str):
                    self.persistence.save_message("user", user_input)
                    
                    # Auto-titling for new sessions
                    if not self.persistence.has_title():
                        try:
                            title_prompt = (
                                f"Create a very concise (max 5 words) and descriptive title for a new conversation that starts with this message: \"{user_input}\". "
                                "Respond ONLY with the title text, no quotes or preamble."
                            )
                            title = self.provider.generate_response([{"role": "user", "content": title_prompt}])
                            if title and title.strip():
                                # Clean up common AI artifacts if any
                                title = title.strip().strip('"')
                                self.persistence.set_session_title(title)
                                logger.info(f"[Engine] Auto-titled session: {title}")
                        except Exception as e:
                            logger.error(f"[Engine] Failed to auto-title session: {e}")
                
                # Conversation loop for tool calling
                while True:
                    self.current_channel.show_activity("typing")
                    messages = [{"role": "system", "content": self.system_prompt}]
                    messages.extend(self.persistence.load_history())
                    tool_schemas = [t["schema"] for t in self.tools.values()] if self.tools else None
                    response = self.provider.generate_response(messages, tools=tool_schemas)
                    
                    if isinstance(response, dict) and "tool_call" in response:
                        tc = response["tool_call"]
                        tool_name = tc["name"]
                        args = tc["args"]
                        
                        if tool_name in self.tools:
                            # Send technical status update
                            display_name = self.tools[tool_name]["display_name"]
                            self.current_channel.send_status(f"{display_name}...")
                            self.current_channel.show_activity("upload_document")
                            
                            try:
                                # Save model's tool call structurally
                                self.persistence.save_message("model", "", tool_call=tc)
                                
                                # Add workspace dir to args for some tools if needed
                                args["_workspace"] = self.workspace_dir
                                if self.host_workspace_dir:
                                    args["_host_workspace"] = self.host_workspace_dir
                                
                                # Inject Scheduler
                                args["_scheduler"] = self.scheduler
                                
                                # Inject Channel Name
                                args["_channel_name"] = getattr(self.current_channel, "name", "terminal")

                                # Execute tool
                                result = self.tools[tool_name]["execute"](args)
                                
                                # Post-tool: Scan workspace/output for new files
                                sent_info = self._scan_and_send_output_files()
                                if sent_info:
                                    result = f"{result}\n\n{sent_info}"

                                # Save tool result structurally
                                self.persistence.save_message("tool", result, name=tool_name, tool_result={"result": result})
                                
                                continue # Loop back to provider with result
                            except Exception as e:
                                error_msg = f"Error executing tool {tool_name}: {str(e)}"
                                self.current_channel.send_output(error_msg)
                                self.persistence.save_message("assistant", error_msg)
                                break
                        else:
                            error_msg = f"Tool {tool_name} not found."
                            self.current_channel.send_output(error_msg)
                            self.persistence.save_message("assistant", error_msg)
                            break 

                    # Suppress "silent" responses if the model is just signaling the end of a turn
                    is_silent = isinstance(response, str) and response.strip() in ("", "_", ".")
                    if not is_silent and response:
                        if isinstance(response, dict):
                            # Fallback for unexpected dict response without tool_call
                            response = str(response)
                        
                        self.current_channel.send_output(response)
                        self.persistence.save_message("assistant", str(response))
                    else:
                        logger.info("[Engine] Suppressing silent text response.")
                        # Ensure activity stops even for silent responses
                        self.current_channel.stop_activity()
                    break 

                # Auto-compact check
                if self.context_compact_threshold:
                    usage = self.provider.get_usage()
                    total_tokens = usage.get('total_tokens', 0)
                    if total_tokens > self.context_compact_threshold:
                        logger.info(f"[Engine] Token usage {total_tokens} exceeds threshold {self.context_compact_threshold}. Compacting...")
                        self._handle_compact()

        except KeyboardInterrupt:
            for channel in self.channels:
                channel.send_output("\nInterrupted by user. Goodbye!")
        finally:
            # Explicit cleanup
            logger.info("[Engine] Shutting down...")
            self.scheduler.stop()
            for channel in self.channels:
                if hasattr(channel, "stop_activity"):
                    channel.stop_activity()

    def _scan_and_send_output_files(self) -> str:
        """Scans the workspace/output directory and sends files via the active channel. 
        Returns a string summary of sent files."""
        output_dir = os.path.join(self.workspace_dir, "output")
        if not os.path.exists(output_dir):
            return ""

        sent_files = []
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path):
                # Move to a 'processed' folder first to get the final path
                processed_dir = os.path.join(self.workspace_dir, "processed")
                if not os.path.exists(processed_dir):
                    os.makedirs(processed_dir)
                
                final_path = os.path.join(processed_dir, filename)
                shutil.move(file_path, final_path)
                
                # Send the file with the accurate path to the ACTIVE channel
                self.current_channel.send_file(final_path, caption=f"I've generated a file: {filename}")
                
                # Report the sandboxed path to the model
                sandboxed_path = f"/workspace/processed/{filename}"
                sent_files.append(sandboxed_path)

        if sent_files:
            summary = "The following files were generated and successfully sent to the user. From the perspective of the sandbox, they are now located at:\n"
            for f in sent_files:
                summary += f"- {f}\n"
            return summary
        
        return ""
