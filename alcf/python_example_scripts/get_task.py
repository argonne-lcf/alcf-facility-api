import os
import requests
import json
from dotenv import load_dotenv
load_dotenv()

# Define your task ID
task_id = "6daa409a-09a8-4b76-80ad-c9ca51e9d461"

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/task/{task_id}"

# Send request to Facility API
response = requests.get(url, headers=headers)

# Print response
print(response.status_code)
print(json.dumps(response.json(), indent=2))
