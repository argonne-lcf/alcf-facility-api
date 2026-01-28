import os
import requests
from globus_access_token import get_access_token
from dotenv import load_dotenv
load_dotenv()

# Get Globus access token
ACCESS_TOKEN = get_access_token()

# Targeted resource
resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith

# Build input data
data = {
    "path": "/home/bcote"
}

# Build headers
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/filesystem/ls/{resource_id}"

# Send request to Facility API
response = requests.get(url, params=data, headers=headers)

# Print response
print(response.status_code)
print(response.json())
