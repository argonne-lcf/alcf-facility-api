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
def submit(resource_id=None, data=None, function=None, method=None):

    # Build URL
    url = f"{os.getenv('BASE_URL')}/filesystem/{function}/{resource_id}"

    # Send request to Facility API
    if method.lower() == "get":
        response = requests.get(url, params=data, headers=HEADERS)
    elif method.lower() == "delete":
        response = requests.delete(url, params=data, headers=HEADERS)
    elif method.lower() == "put":
        response = requests.put(url, json=data, headers=HEADERS)
    elif method.lower() == "post":
        response = requests.post(url, json=data, headers=HEADERS)
    else:
        response = None

    # Print response
    print(response.status_code)
    print(response.json())
