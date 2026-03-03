import os
import requests
from globus_access_token import get_access_token
from dotenv import load_dotenv
load_dotenv()

# Get Globus access token
ACCESS_TOKEN = get_access_token()

# Define headers
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Function to submit Filesystem request to Facility API 
def submit(resource_id=None, data=None, function=None):

    # Build URL
    url = f"{os.getenv('BASE_URL')}/filesystem/{function}/{resource_id}"

    # Send request to Facility API
    response = requests.get(url, params=data, headers=HEADERS)

    # Print response
    print(response.status_code)
    print(response.json())
