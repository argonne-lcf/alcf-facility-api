import json
import os
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

# Request data
capability_id = "75"

# Build headers
headers = {
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/account/capabilities/{capability_id}"

# Send request to Facility API
response = requests.get(url, headers=headers)
print(response.status_code)
print(json.dumps(response.json(), indent=2))
