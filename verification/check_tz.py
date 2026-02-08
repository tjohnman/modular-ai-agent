from datetime import datetime
import time
import os

print(f"Timezone name: {time.tzname}")
print(f"datetime.now(): {datetime.now()}")
print(f"datetime.utcnow(): {datetime.utcnow()}")
try:
    from zoneinfo import ZoneInfo
    print(f"Europe/Madrid time: {datetime.now(ZoneInfo('Europe/Madrid'))}")
except ImportError:
    print("ZoneInfo not available")
except Exception as e:
    print(f"Error getting Madrid time: {e}")
