# 
# AI generated
#

import os
import sys
import time
import json
import logging
import requests

API_CALL_DELAY = 0.5

_current_test: str | None = None
_current_test_log: list[str] = []
_failed_test_logs: dict[str, list[str]] = {}

from dotenv import load_dotenv

logging.disable(logging.WARNING)
from app.routers.compute.models import JobState
from app.routers.task.models import Task, TaskStatus
logging.disable(logging.NOTSET)

load_dotenv(override=True)


def set_current_test(name: str | None) -> None:
    global _current_test, _current_test_log
    _current_test = name
    _current_test_log = []


def _log(line: str) -> None:
    print(line)
    if _current_test is not None:
        _current_test_log.append(line)


def _save_failed_log() -> None:
    if _current_test is not None and _current_test_log:
        _failed_test_logs[_current_test] = list(_current_test_log)


def get_env(key: str, required: bool = True) -> str:
    value = os.getenv(key)
    if required and not value:
        print(f"[ERROR] Missing required environment variable: {key}")
        print("        Copy .env.example to .env and fill in the values.")
        sys.exit(1)
    return value or ""


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {get_env('ACCESS_TOKEN')}",
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

    time.sleep(API_CALL_DELAY)

    if response.status_code != expected:
        _log(f"  [FAIL] {label}: expected HTTP {expected}, got {response.status_code}")
        _log(pretty(body) if body is not None else response.text)
        _save_failed_log()
        sys.exit(1)

    _log(f"  [OK]   {label} -> HTTP {response.status_code}")
    if body is not None:
        _log(pretty(body))
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
            _log(f"  [WARN] Task poll HTTP {response.status_code}")
            time.sleep(poll_interval)
            continue

        task = Task.model_validate(response.json())

        if verbose:
            _log(f"  [POLL] Task {task.id} status: {task.status.value}")

        if task.status == TaskStatus.completed:
            _log(pretty(task.model_dump()))
            return task
        if task.status == TaskStatus.failed:
            _log(f"  [FAIL] Task {task.id} ended with status: {task.status.value}")
            _log(pretty(task.model_dump()))
            _save_failed_log()
            sys.exit(1)

        time.sleep(poll_interval)

    _log(f"  [FAIL] Task {task_id} did not complete within {timeout}s")
    _save_failed_log()
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
                    _log(f"  [POLL] Job {job_id} state: {state}")
                if state in terminal_states:
                    _log(pretty(data))
                    return data
                break
            elif historical == "true":
                if verbose:
                    _log(f"  [WARN] Job poll attempt {attempt}: HTTP {response.status_code}")

        time.sleep(poll_interval)

    _log(f"  [FAIL] Job {job_id} did not reach terminal state within {timeout}s")
    _save_failed_log()
    sys.exit(1)


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def result_summary(passed: list[str], failed: list[str]) -> None:
    if failed and _failed_test_logs:
        print(f"\n{'=' * 60}")
        print("  FAILURE DETAILS")
        print("=" * 60)
        for name, lines in _failed_test_logs.items():
            print(f"\n  -- {name} --")
            for line in lines:
                print(line)

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
