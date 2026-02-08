from datetime import datetime

# Check what astimezone() gives us
local_aware = datetime.now().astimezone()
print(f"Local aware time: {local_aware}")
print(f"Timezone info: {local_aware.tzinfo}")
print(f"Timezone name: {local_aware.tzname()}")
