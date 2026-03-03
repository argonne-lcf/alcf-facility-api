import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Targeted resource
resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith
job_id = "78337"

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv("ACCESS_TOKEN", None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/compute/cancel/{resource_id}/{job_id}"

# Send request to Facility API
response = requests.delete(url, headers=headers)
print(response.status_code)
if response.status_code == 204:
    print("Canceled")
else:
    print(response.json())
