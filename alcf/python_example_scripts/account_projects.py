import json
import os
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/account/projects"

# Send request to Facility API
response = requests.get(url, headers=headers)
print(response.status_code)
print(json.dumps(response.json(), indent=2))
