import json
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

headers = {
    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN', None)}",
    "Content-Type": "application/json"
}
base_url = os.getenv("BASE_URL")

projects = requests.get(f"{base_url}/account/projects", headers=headers, timeout=10).json()

for project in projects:
    project_id = project["id"]
    project_name = project["name"]

    allocations = requests.get(
        f"{base_url}/account/projects/{project_id}/project_allocations",
        headers=headers,
        timeout=10
    ).json()

    if not allocations:
        continue

    print(f"\nProject: {project_name}")
    for alloc in allocations:
        capability = alloc["capability_uri"].rstrip("/").split("/")[-1]
        for entry in alloc["entries"]:
            allocation = entry["allocation"]
            usage = entry["usage"]
            unit = entry["unit"]
            print(f"  [{capability}]  allocation={allocation}  usage={usage}  unit={unit}")
