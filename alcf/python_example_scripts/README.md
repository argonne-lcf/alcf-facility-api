# Python Examples

## Quick virtual environment

Create a virtual environment:
```bash
cd alcf/python_example_scripts
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Prepare your `.env` file

```bash
BASE_URL=<API-base-url>
#BASE_URL="http://localhost:8000/api/v1" # local dev
#BASE_URL="https://api-dev.alcf.anl.gov/api/v1" # internal server (need VPN)
#BASE_URL="https://api.alcf.anl.gov/api/v1" # production server
```

## Keycloak Access Token for Compute Operations

Make sure the token script is executable:
```bash
chmod u+x keycloak_access_token.sh
```

Execute the auth script and enter your username and MobilePass+ credentials:
```bash
sh keycloak_access_token.sh
```

Copy the `access_token` field from the response and add it to your `.env` file as `ACCESS_TOKEN=...`.

## Compute Operations

Execute any of the `compute_....py` file. Make sure you adjust the input parameters in the files. When you submit a job through `compute_submit_job.py`, make sure you adjust the `stdout_path` and `stderr_path` variable in the file to point to a directory you can access.

## Globus Access Token for Filesystem Operations

The `globus_access_token.py` script helps you authenticate with Globus and obtain access tokens for filesystem operations. Authenticate with your ALCF account:
```bash
python globus_access_token.py authenticate
```

You can view your access token with:
```bash
python globus_access_token.py get_access_token
```

Copy the `access_token` field from the response and add it to your `.env` file as `ACCESS_TOKEN=...`.

If you need to authenticate with another identity, logout from Globus by visiting [https://app.globus.org/logout](https://app.globus.org/logout), and start the process over.

## Filesystem Operations

Execute any of the `filesystem_....py` file. Make sure you adjust the input parameters in the files. This should give you back a task ID. 

Use the `get_task.py` file to recover your result (or see the status). Make sure you include your `task_id` in the file.

## Access Dev API with SSH Tunnel

If you need to access the internal dev API from outside Argonne's network, you can create an ssh tunnel through one of the ALCF login node:
```bash
ssh -N -D 8001 <your-username>@edtb-02.alcf.anl.gov
```

You can verify the tunnel on port 8001 with:
```bash
ps aux | grep 8001
```

With `curl`, make queries through SOCKS5 to avoid SSL certificate issues:
```
curl -x socks5h://127.0.0.1:8001 https://api-dev.alcf.anl.gov/api/v1/status/resources
```

With `python`, make sure you `requests` is installed with the `socks` option:
```bash
pip install "requests[socks]"
```

Then query the API with:
```python
import requests

proxies = {"https": "socks5h://127.0.0.1:8001"}

response = requests.get("https://api-dev.alcf.anl.gov/api/v1/status/resources", proxies=proxies)

print(response.status_code)
print(response.text)
```
