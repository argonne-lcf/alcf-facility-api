import os
import requests
from globus_access_token import get_access_token
from dotenv import load_dotenv
load_dotenv()

# Define your task ID
task_id = "2c99e2aa-b3bf-4ab7-afd3-4e7c36e0ebc8"

# Get Globus access token
ACCESS_TOKEN = get_access_token()

# Targeted resource
resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith

# Build headers
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/task/{task_id}"

# Send request to Facility API
response = requests.get(url, headers=headers)

# Print response
print(response.status_code)
print(response.json())
