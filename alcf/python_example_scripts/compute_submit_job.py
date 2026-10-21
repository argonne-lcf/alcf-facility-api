import json
import os
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

# Targeted resource
resource_id = "55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris

# Build commands (everything the qsub would have, besides the #PBS instructions)
commands = """
echo Start
sleep 10
pwd
echo $TEST_ENV
echo End
"""

# Build input data
data = {
    "executable": "/bin/bash",
    "arguments": ["-lc", commands],
    "name": "TEST",
    "stdout_path": "/home/bcote/qsub",
    "stderr_path": "/home/bcote/qsub",
    "environment": {"TEST_ENV": "It's working!"},
    "resources": {
        "memory": 2222,
        "node_count": 1,
        "cpu_cores_per_process": 64,
    },
    "attributes": {
        "duration": 300,
        "queue_name": "debug",
        "account": "iri_api",
        "custom_attributes": {"filesystems": "eagle"}
    }
}

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/compute/job/{resource_id}"

# Send request to Facility API
response = requests.post(url, json=data, headers=headers)

# Print response
print(response.status_code)
print(json.dumps(response.json(), indent=2))
