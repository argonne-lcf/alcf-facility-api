import json
import os
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

# Request data
project_id = "ded53b0e-e160-303a-90d0-3cdbd5d39563"

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/account/projects/{project_id}"

# Send request to Facility API
response = requests.get(url, headers=headers)
print(response.status_code)
print(json.dumps(response.json(), indent=2))
