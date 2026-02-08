import os
import sys
import time
import requests
from dotenv import load_dotenv

def main():
    print("--- Telegram Bot Setup ---")
    print("This script will help you configure your Telegram Bot for the Agent Project.")
    print("\n1. Create a bot with @BotFather on Telegram.")
    print("2. Get your API Token.")
    
    token = input("\nEnter your Telegram Bot Token: ").strip()
    if not token:
        print("Error: Token is required.")
        return

    print("\nAttempting to verify token...")
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
        if not resp.get("ok"):
            print(f"Error: Invalid token. {resp.get('description')}")
            return
        bot_username = resp['result']['username']
        print(f"Success! Bot found: @{bot_username}")
    except Exception as e:
        print(f"Error connecting to Telegram API: {e}")
        return

    print(f"\n3. Now, send any message to @{bot_username} from your Telegram account.")
    print("   This script will wait until it receives a message to identify your Chat ID.")
    
    chat_id = None
    offset = 0
    print("Waiting for a message...")
    
    try:
        timeout = 60 # 60 seconds timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"offset": offset, "timeout": 5}).json()
            if resp.get("ok") and resp.get("result"):
                for update in resp["result"]:
                    if "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        user_name = update["message"]["from"].get("username", update["message"]["from"].get("first_name", "User"))
                        print(f"\nReceived message from {user_name} (Chat ID: {chat_id})")
                        break
                if chat_id:
                    break
            time.sleep(1)
            print(".", end="", flush=True)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return

    if not chat_id:
        print("\nTimed out waiting for a message. Please try again.")
        return

    print(f"\n4. Configuration complete!")
    print(f"   TELEGRAM_BOT_TOKEN={token}")
    print(f"   TELEGRAM_CHAT_ID={chat_id}")

    confirm = input("\nWould you like to save these to your .env file? (y/n): ").strip().lower()
    if confirm == 'y':
        env_path = ".env"
        current_env = {}
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        current_env[k] = v
        
        current_env["TELEGRAM_BOT_TOKEN"] = token
        current_env["TELEGRAM_CHAT_ID"] = str(chat_id)
        
        with open(env_path, "w") as f:
            for k, v in current_env.items():
                f.write(f"{k}={v}\n")
        
        print(f"Successfully updated {env_path}")
    else:
        print("Skipped updating .env file.")

if __name__ == "__main__":
    main()
