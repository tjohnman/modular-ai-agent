# Modular AI Agent

A modular, extensible AI agent system powered by Google's Gemini API with multi-channel support, dynamic tool loading, and persistent session management.

## Features

- **Multi-Provider Support**: Built with Google Gemini API and NanoGPT (easily extensible to other LLM providers)
- **Multi-Channel I/O**: Interact via Terminal or Telegram
- **Dynamic Tool System**: Hot-loadable tools with automatic discovery
- **Session Management**: Persistent conversation history with multi-session support
- **Task Scheduling**: Schedule one-time or recurring tasks with cron expressions
- **Sandboxed Execution**: Run Python code safely in isolated Docker containers
- **Audio Support**: Transcribe audio messages and generate speech
- **Web Search**: Integrated DuckDuckGo search capabilities
- **File Handling**: Automatic file processing and delivery pipeline

## Architecture

The system follows a clean, modular architecture:

```
┌─────────────────────────────────────────────────┐
│                    Engine                       │
│  (Orchestrates conversation loop & commands)    │
└──────────┬──────────────────────┬───────────────┘
           │                      │
    ┌──────▼──────┐        ┌──────▼──────┐
    │  Provider   │        │   Channel   │
    │  (Gemini)   │        │ (Terminal/  │
    │             │        │  Telegram)  │
    └─────────────┘        └─────────────┘
           │                      │
    ┌──────▼──────────────────────▼───────────┐
    │         Persistence Layer                │
    │    (JSONL session logs & state)          │
    └──────────────────────────────────────────┘
```

### Core Components

- **Engine**: Orchestrates the conversation loop, command parsing, and tool execution
- **Provider**: Abstract interface for LLM communication (Google GenAI SDK implementation)
- **Channel**: Abstract I/O interface with Terminal and Telegram implementations
- **Persistence**: Handles JSONL session logging and state management
- **Scheduler**: Manages scheduled tasks with cron support
- **Dynamic Tools**: Runtime-loaded tools from the `tools/` directory

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for the `python_analyser` tool)
- Google API Key (for Gemini)
- (Optional) Telegram Bot Token for remote access

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agent-project
   ```

2. **Run the setup script**
   ```bash
   bash scripts/setup.sh
   ```
   
   This will:
   - Create a Python virtual environment
   - Install all dependencies
   - Pull required Docker images
   - Optionally configure Telegram integration
   - Create `.env` from `.env.example`

3. **Configure environment variables**
   
   Edit `.env` and add your credentials:
   ```bash
   GOOGLE_API_KEY=your_google_api_key_here
   NANOGPT_API_KEY=your_nano_gpt_api_key_here
   TELEGRAM_BOT_TOKEN=your_bot_token_here  # Optional
   TELEGRAM_CHAT_ID=your_chat_id_here      # Optional
   WORKSPACE_HOST_PATH=/absolute/path/to/workspace  # For Docker
   ```

4. **Configure channels**
   
   Edit `config.json` (created from `config.json.example`) to select your channels and settings:
   ```json
   {
       "provider": "google",
       "channels": ["terminal", "telegram"],
       "google": {
           "model": "gemini-3-flash-preview",
           "context_compact_threshold": 100000
       },
       "sessions_dir": "sessions"
   }
   ```

That's it! The setup script will prompt you to deploy the application, which automatically starts the agent as a service. If you declined deployment during setup, you can run it later with `bash scripts/deploy.sh`.

## Configuration

### Environment Variables (`.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Your Google Gemini API key | Required for Google provider |
| `NANOGPT_API_KEY` | Your NanoGPT API key | Required for NanoGPT provider |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | If using Telegram |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | If using Telegram |
| `WORKSPACE_HOST_PATH` | Absolute path to workspace directory on host | For Docker deployment |

### Configuration File (`config.json`)

| Field | Description | Default |
|-------|-------------|---------|
| `provider` | LLM provider to use | `"google"` |
| `channels` | Array of channels to enable | `["terminal"]` |
| `google.model` | Gemini model name | `"gemini-3-flash-preview"` |
| `google.context_compact_threshold` | Token count threshold for auto-compaction | `100000` |
| `nano_gpt.model` | NanoGPT model name | `"gpt-4o-mini"` |
| `nano_gpt.base_url` | NanoGPT API base URL | `"https://nano-gpt.com/api"` |
| `nano_gpt.timeout_seconds` | Request timeout in seconds | `60` |
| `nano_gpt.context_compact_threshold` | Token count threshold for auto-compaction | `100000` |
| `sessions_dir` | Directory for session storage | `"sessions"` |

**Example configurations:**

Terminal only:
```json
{
    "provider": "google",
    "channels": ["terminal"],
    "google": {
        "model": "gemini-3-flash-preview",
        "context_compact_threshold": 100000
    },
    "sessions_dir": "sessions"
}
```

Multi-channel (Terminal + Telegram):
```json
{
    "provider": "google",
    "channels": ["terminal", "telegram"],
    "google": {
        "model": "gemini-3-flash-preview",
        "context_compact_threshold": 100000
    },
    "sessions_dir": "sessions"
}
```

NanoGPT:
```json
{
    "provider": "nano_gpt",
    "channels": ["terminal"],
    "nano_gpt": {
        "model": "zai-org/glm-4.7",
        "base_url": "https://nano-gpt.com/api",
        "timeout_seconds": 60,
        "context_compact_threshold": 200000
    },
    "sessions_dir": "sessions"
}
```

## Usage

### Slash Commands

The agent supports built-in commands for management:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/usage` | Show token usage for current session |
| `/compact` | Compact conversation history to save context |
| `/clear` | Clear history and start new session |
| `/reset` | Reset workspace (deletes all workspace files) and start new session |
| `/reload` | Reload system prompt and tools |
| `/new [title]` | Create a new session with optional title |
| `/list` | List all available sessions |
| `/switch [index]` | Switch to a different session |
| `/name [title]` | Rename the current session |
| `/exit` or `/quit` | Terminate the agent |

### Example Interactions

**Web Search:**
```
You: Search for the latest news about AI
Agent: [Uses web_search tool to find results]
```

**Python Code Execution:**
```
You: Create a plot of sine and cosine waves
Agent: [Uses python_analyser to generate and save plot]
Agent: [Automatically sends the generated image]
```

**Task Scheduling:**
```
You: Remind me to check emails in 30 minutes
Agent: [Uses schedule_task to create a reminder]
```

**Audio Transcription:**
```
[Send voice message via Telegram]
Agent: [Transcribes audio and responds to content]
```

## Dynamic Tool System

Tools are automatically discovered and loaded from the `tools/` directory at runtime.

### Available Tools

| Tool | Description |
|------|-------------|
| `get_current_time` | Returns current system date and time |
| `web_search` | Performs web searches via DuckDuckGo |
| `python_analyser` | Runs Python code in sandboxed Docker container with full network access, compilers, system administration tools, and more |
| `transcribe_audio` | Transcribes audio files using Faster Whisper |
| `text_to_speech` | Generates speech from text using Piper TTS |
| `schedule_task` | Schedules tasks with cron or one-time execution |
| `list_tasks` | Lists all scheduled tasks |
| `delete_task` | Deletes a scheduled task by ID |

### Creating Custom Tools

Create a new Python file in `tools/` with this structure:

```python
# tools/my_tool.py

SCHEMA = {
    "name": "my_tool_name",
    "display_name": "Running my tool",  # Optional: shown during execution
    "description": "What the tool does (for the LLM)",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "param1": {
                "type": "STRING",
                "description": "Description of param1"
            }
        },
        "required": ["param1"]
    }
}

def execute(params: dict) -> str:
    """Execute the tool logic."""
    # params['_workspace'] is automatically injected
    param1 = params.get("param1")
    return f"Result: {param1}"
```

The tool will be automatically loaded on next startup or after `/reload`.

## Docker Deployment

Deploy as a persistent service using Docker Compose:

```bash
# Deploy the service
bash scripts/deploy.sh

# View logs
docker logs -f agent-system

# Stop the service
docker compose -f deploy/docker-compose.yml down
```

The deployment includes:
- Automatic restart on failure
- Volume mounts for persistence (sessions, workspace, logs)
- Docker socket access for `python_analyser` tool
- Timezone detection and configuration

## Project Structure

```
.
├── agent_system/           # Core system modules
│   ├── channels/          # I/O channel implementations
│   ├── core/              # Engine, provider, scheduler
│   ├── providers/         # LLM provider implementations
│   └── utils/             # Logging and utilities
├── tools/                 # Dynamic tool modules
├── scripts/               # Setup and deployment scripts
├── deploy/                # Docker configuration
├── memory/                # System prompts and state
├── sessions/              # Persistent session logs
├── workspace/             # Shared workspace for tools
├── verification/          # Test suite
├── config.json            # Runtime configuration
├── .env                   # Environment variables (create from .env.example)
├── requirements.txt       # Python dependencies
└── main.py               # Application entry point
```

## Testing

Run the verification suite:

```bash
# Activate virtual environment
source venv/bin/activate

# Run specific tests
python verification/test_telegram_channel.py
python verification/test_audio_support.py
python verification/test_scheduler_integration.py

# Run all tests
python -m unittest discover verification/
```

## Security Considerations

- **Sandboxed Execution**: Python code runs in isolated Docker containers
- **Environment Variables**: Sensitive credentials stored in `.env` (gitignored)
- **Telegram**: Bot only responds to configured `TELEGRAM_CHAT_ID`
- **Docker Socket**: Required for `python_analyser` but grants container access

## Contributing

Contributions are welcome! Areas for improvement:

- Additional LLM providers (OpenAI, Anthropic, etc.)
- New I/O channels (Discord, Slack, Web UI)
- More built-in tools
- Enhanced error handling
- Performance optimizations

## License

GNU Affero General Public License (AGPL)

## Acknowledgments

- Built with [Google Gemini API](https://ai.google.dev/)
- Uses [Faster Whisper](https://github.com/guillaumekln/faster-whisper) for audio transcription
- Uses [Piper TTS](https://github.com/rhasspy/piper) for text-to-speech
- Web search powered by [DuckDuckGo](https://duckduckgo.com/)

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Note**: This is an experimental AI agent system. Use responsibly and review all generated code before execution.
