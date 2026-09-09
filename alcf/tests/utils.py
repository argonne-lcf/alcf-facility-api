# 
# AI generated
#

import os
import sys
import time
import json
import logging
import requests
import globus_sdk
from dotenv import load_dotenv

logging.disable(logging.WARNING)
from app.routers.compute.models import JobState
from app.routers.task.models import Task, TaskStatus
logging.disable(logging.NOTSET)

load_dotenv(override=True)

# Facility API Globus scope
SCOPE_CLIENT_ID = "6be511f6-a071-471f-9bc0-02a0d0836723"
SCOPE_STRING = f"https://auth.globus.org/scopes/{SCOPE_CLIENT_ID}/filesystem"

# Globus service account
CLIENT_ID = os.getenv("GLOBUS_CONFIDENTIAL_CLIENT_ID", None)
CLIENT_SECRET = os.getenv("GLOBUS_CONFIDENTIAL_CLIENT_SECRET", None)
USE_SERVICE_ACCOUNT = os.getenv("USE_SERVICE_ACCOUNT", "False").lower() in ("true", "1", "t")

# Access token
if USE_SERVICE_ACCOUNT:
    if CLIENT_ID is None or CLIENT_SECRET is None:
        print("No confidential client credentials.")
        sys.exit(1)
    client = globus_sdk.ConfidentialAppAuthClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    token_response = client.oauth2_client_credentials_tokens(requested_scopes=[SCOPE_STRING])
    ACCESS_TOKEN = token_response.by_resource_server[SCOPE_CLIENT_ID]["access_token"]
else:
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    

def get_env(key: str, required: bool = True) -> str:
    value = os.getenv(key)
    if required and not value:
        print(f"[ERROR] Missing required environment variable: {key}")
        print("        Copy .env.example to .env and fill in the values.")
        sys.exit(1)
    return value or ""


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def get_base_url() -> str:
    return get_env("BASE_URL").rstrip("/")


def print_response(label: str, response: requests.Response, verbose: bool = True) -> None:
    status = response.status_code
    ok = 200 <= status < 300
    symbol = "OK" if ok else "FAIL"
    print(f"  [{symbol}] {label} -> HTTP {status}")
    if verbose:
        try:
            print(json.dumps(response.json(), indent=4))
        except Exception:
            print(response.text)


def pretty(data: dict | list) -> str:
    return json.dumps(data, indent=4)


def assert_status(label: str, response: requests.Response, expected: int = 200) -> dict:
    try:
        body = response.json()
    except Exception:
        body = None

    if response.status_code != expected:
        print(f"  [FAIL] {label}: expected HTTP {expected}, got {response.status_code}")
        print(pretty(body) if body is not None else response.text)
        sys.exit(1)

    print(f"  [OK]   {label} -> HTTP {response.status_code}")
    if body is not None:
        print(pretty(body))
    return body or {}


def wait_for_task(
    task_id: str,
    poll_interval: float | None = None,
    timeout: float | None = None,
    verbose: bool = True,
) -> Task:
    base_url = get_base_url()
    headers = get_headers()
    poll_interval = poll_interval or float(get_env("TASK_POLL_INTERVAL") or 5)
    timeout = timeout or float(get_env("TASK_TIMEOUT") or 120)

    url = f"{base_url}/task/{task_id}"
    deadline = time.time() + timeout

    while time.time() < deadline:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"  [WARN] Task poll HTTP {response.status_code}")
            time.sleep(poll_interval)
            continue

        task = Task.model_validate(response.json())

        if verbose:
            print(f"  [POLL] Task {task.id} status: {task.status.value}")

        if task.status == TaskStatus.completed:
            print(pretty(task.model_dump()))
            return task
        if task.status == TaskStatus.failed:
            print(f"  [FAIL] Task {task.id} ended with status: {task.status.value}")
            print(pretty(task.model_dump()))
            sys.exit(1)

        time.sleep(poll_interval)

    print(f"  [FAIL] Task {task_id} did not complete within {timeout}s")
    sys.exit(1)


TERMINAL_JOB_STATES = {
    JobState.COMPLETED.value,
    JobState.FAILED.value,
    JobState.CANCELED.value
}


def extract_job_state(data: dict) -> str:
    status_field = data.get("status") or {}
    if isinstance(status_field, dict):
        return (status_field.get("state") or "").lower()
    return (status_field or data.get("state") or "").lower()


def wait_for_job(
    resource_id: str,
    job_id: str,
    terminal_states: set | None = None,
    poll_interval: float | None = None,
    timeout: float | None = None,
    verbose: bool = True,
) -> dict:
    base_url = get_base_url()
    headers = get_headers()
    poll_interval = poll_interval or float(get_env("TASK_POLL_INTERVAL") or 5)
    timeout = timeout or float(get_env("JOB_TIMEOUT") or 600)
    if terminal_states is None:
        terminal_states = TERMINAL_JOB_STATES

    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1

        # After a job ends it disappears from the active queue; use historical=true
        for historical in ("false", "true"):
            url = f"{base_url}/compute/status/{resource_id}/{job_id}?historical={historical}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                state = extract_job_state(data)
                if verbose:
                    print(f"  [POLL] Job {job_id} state: {state}")
                if state in terminal_states:
                    print(pretty(data))
                    return data
                break
            elif historical == "true":
                if verbose:
                    print(f"  [WARN] Job poll attempt {attempt}: HTTP {response.status_code}")

        time.sleep(poll_interval)

    print(f"  [FAIL] Job {job_id} did not reach terminal state within {timeout}s")
    sys.exit(1)


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def result_summary(passed: list[str], failed: list[str]) -> None:
    print(f"\n{'=' * 60}")
    print("  TEST SUMMARY")
    print("=" * 60)
    for name in passed:
        print(f"  [PASS] {name}")
    for name in failed:
        print(f"  [FAIL] {name}")
    total = len(passed) + len(failed)
    print(f"\n  {len(passed)}/{total} tests passed")
    if failed:
        sys.exit(1)
