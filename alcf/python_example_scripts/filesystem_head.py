import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Targeted resource
#resource_id = "7f7d0593-162e-43b9-8476-07d7d137d6ab" # Edith
#resource_id = "9674c7e1-aecc-4dbb-bf01-c9197e027cd6" # Sophia
resource_id = "1c3ad9d4-2e91-42bc-becb-72b1fde1235c" # Eagle

# Build input data
data = {
    "path": "/home/bcote/test.txt",
    "lines": 3
}

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/filesystem/head/{resource_id}"

# Send request to Facility API
response = requests.get(url, params=data, headers=headers)

# Print response
print(response.status_code)
print(response.json())
