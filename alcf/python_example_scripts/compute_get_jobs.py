import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Targeted resource
resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith
historical = False
limit = 0
offset = 0

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv("ACCESS_TOKEN", None)}",
    "Content-Type": "application/json"
}

# Build URL
historical = "true" if historical else "false"
url = f"http://localhost:8000/api/v1/compute/status/{resource_id}?historical={historical}&limit={limit}&offset={offset}"

# Send request to Facility API
response = requests.post(url, headers=headers)
print(response.status_code)
print(response.json())
