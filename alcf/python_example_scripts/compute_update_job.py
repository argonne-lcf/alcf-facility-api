import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Targeted resource
#resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith
resource_id = "55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris

# Request data
job_id = "6958717"
data = {
    "name": "updated_named",
    "attributes": {
        "account": "datascience",
    }
}

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv("ACCESS_TOKEN", None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/compute/job/{resource_id}/{job_id}"

# Send request to Facility API
response = requests.put(url, json=data, headers=headers)
print(response.status_code)
print(response.json())
