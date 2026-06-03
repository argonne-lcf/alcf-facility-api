import json
import os
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

# Request data
name = None
limit = 100
offset = 0

# Build headers
headers = {
    "Content-Type": "application/json"
}

# Build input data
params = {
    "name": name,
    "limit": limit, 
    "offset": offset
}

# Build URL
url = f"{os.getenv('BASE_URL')}/account/capabilities"

# Send request to Facility API
response = requests.get(url, params=params, headers=headers)
print(response.status_code)
print(json.dumps(response.json(), indent=2))
