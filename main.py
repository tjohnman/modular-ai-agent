import os
import sys
import docker
from dotenv import load_dotenv
from agent_system.core.engine import Engine
from agent_system.providers.google_provider import GoogleProvider
from agent_system.channels.terminal_channel import TerminalChannel
from agent_system.utils import logger
from utils.persistence import Persistence
from utils.config import load_config

def check_docker():
    """Checks if the Docker daemon is running."""
    try:
        client = docker.from_env()
        client.ping()
        logger.info("Docker daemon is running.")
    except Exception as e:
        error_msg = "Docker daemon is not running. Please make sure Docker Desktop or your local Docker daemon is active."
        print(f"\nERROR: {error_msg}")
        print(f"Details: {e}\n")
        logger.error(error_msg)
        logger.error(f"Error: {e}")
        sys.exit(1)

def main():
    # Load environment variables from .env
    load_dotenv()
    
    # Load configuration
    config = load_config()
    
    # Initialize components
    # For now, we only have one provider and one channel
    api_key = os.getenv("GOOGLE_API_KEY")
    provider_name = config.get("provider", "google")
    
    if provider_name == "google":
        model_name = config.get("google", {}).get("model", "gemini-3-flash-preview")
        provider = GoogleProvider(api_key=api_key, model_name=model_name)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
    
    # Initialize channels
    channels = []
    channel_names = config.get("channels", ["terminal"])
    if not isinstance(channel_names, list):
        channel_names = [channel_names]
    
    for name in channel_names:
        if name == "terminal":
            channels.append(TerminalChannel())
        elif name == "telegram":
            from agent_system.channels.telegram_channel import TelegramChannel
            channels.append(TelegramChannel())
        else:
            logger.warning(f"Unsupported channel: {name}")
    
    if not channels:
        raise ValueError("No valid channels configured.")
    
    persistence = Persistence(sessions_dir=config.get("sessions_dir", "sessions"))
    
    # Extract context compact threshold
    provider_settings = config.get(provider_name, {})
    context_compact_threshold = provider_settings.get("context_compact_threshold")

    # Initialize and run the engine
    engine = Engine(provider=provider, channels=channels, persistence=persistence, context_compact_threshold=context_compact_threshold)
    engine.run()

if __name__ == "__main__":
    check_docker()
    main()