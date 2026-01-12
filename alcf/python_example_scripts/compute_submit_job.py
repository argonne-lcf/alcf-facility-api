import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Targeted resource
resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith

# Build commands (everything the qsub would have, besides the #PBS instructions)
commands = """
echo Start
sleep 10
echo "slept for 10 secs"
sleep 60
echo "using following python executable"
which python
echo "executing python file"
python test.py
"""

# Convert commands into a single-line string separated with ";" and escaped quotes
commands = commands.strip()
commands = "; ".join(line.strip() for line in commands.splitlines() if line.strip())
commands = commands.replace('"', '\\"')

# Build input data
data = {
    "executable": "/bin/bash",
    "arguments": ["-c", commands],
    "name": "TEST",
    "stdout_path": "/home/bcote/qsub/",
    "stderr_path": "/home/bcote/qsub/",
    "resources": {
        "memory": 2222
    },
    "attributes": {
        "duration": "PT12M",
        "queue_name": "workq"
    }
}

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv("ACCESS_TOKEN", None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"http://localhost:8000/api/current/compute/job/{resource_id}"

# Send request to Facility API
response = requests.post(url, json=data, headers=headers)

# Print response
print(response.status_code)
print(response.json())
