import json
import os
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

# Targeted resource
#resource_id = "55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris
resource_id = "8b9b42f7-572a-4909-8472-a0453436304c" # Crux

# Request data
job_id = "78335"
historical = True

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}

# Build URL
historical = "true" if historical else "false"
url = f"{os.getenv('BASE_URL')}/compute/status/{resource_id}/{job_id}?historical={historical}"

# Send request to Facility API
response = requests.get(url, headers=headers)
print(response.status_code)
print(json.dumps(response.json(), indent=2))
