import os
import requests
import json
from dotenv import load_dotenv
load_dotenv()

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/task"

# Send request to Facility API
response = requests.get(url, headers=headers)

# Print response
print(response.status_code)
print(json.dumps(response.json(), indent=2))
