import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Targeted resource
resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith
job_id = "78335"

# Build input data
data = {
    "name": "updated_named",
}

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv("ACCESS_TOKEN", None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"http://localhost:8000/api/v1/compute/job/{resource_id}/{job_id}"

# Send request to Facility API
response = requests.put(url, json=data, headers=headers)
print(response.status_code)
print(response.json())
