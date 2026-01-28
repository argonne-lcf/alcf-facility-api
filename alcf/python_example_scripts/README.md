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

## Prepare your `.env` file

```bash
BASE_URL=<API-base-url>
#BASE_URL="http://localhost:8000/api/v1" # local dev
#BASE_URL="https://api-dev.alcf.anl.gov/api/v1" # internal server (need VPN)
#BASE_URL="https://api.alcf.anl.gov/api/v1" # production server
```

## Globus Access Token for Filesystem Operations

The `globus_access_token.py` script helps you authenticate with Globus and obtain access tokens for filesystem operations. Authenticate with your ALCF account:
```bash
python globus_access_token.py authenticate
```

You can view your access token with:
```bash
python globus_access_token.py get_access_token
```

If you need to authenticate with another identity, logout from Globus by visiting [https://app.globus.org/logout](https://app.globus.org/logout), and start the process over.

## Filesystem Operations

Execute any of the `filesystem_....py` file. Make sure you adjust the input parameters in the files. This should give you back a task ID. 

Use the `get_task.py` file to recover your result (or see the status). Make sure you include your `task_id` in the file.

