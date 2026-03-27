import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Targeted resource
resource_id = "6115bd2c-957a-4543-abff-5fae52992ff2" # Home
#resource_id = "1c3ad9d4-2e91-42bc-becb-72b1fde1235c" # Eagle

# Build input data
data = {
    "path": "/home/bcote/test.txt",
    "mode": "700"
}

# Build headers
headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}

# Build URL
url = f"{os.getenv('BASE_URL')}/filesystem/chmod/{resource_id}"

# Send request to Facility API
response = requests.put(url, json=data, headers=headers)

# Print response
print(response.status_code)
print(response.json())
