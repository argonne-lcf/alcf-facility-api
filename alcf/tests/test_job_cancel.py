# 
# AI generated
#

import time
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from utils import (
    get_env,
    get_headers,
    get_base_url,
    assert_status,
    wait_for_job,
    extract_job_state,
    section,
    result_summary,
    JobState,
)

BASE_URL = get_base_url()
HEADERS = get_headers()
RESOURCE_ID = get_env("COMPUTE_RESOURCE_ID")
OUTPUT_PATH = get_env("COMPUTE_OUTPUT_PATH")
ACCOUNT = get_env("COMPUTE_ACCOUNT")
QUEUE = get_env("COMPUTE_QUEUE")

passed: list[str] = []
failed: list[str] = []


def record(name: str, ok: bool) -> None:
    (passed if ok else failed).append(name)


# ── Helpers ────────────────────────────────────────────────────────────────────

def submit_job(commands: str, name: str = "TEST_CANCEL") -> dict:
    url = f"{BASE_URL}/compute/job/{RESOURCE_ID}"
    data = {
        "executable": "/bin/bash",
        "arguments": ["-lc", commands],
        "name": name,
        "stdout_path": OUTPUT_PATH,
        "stderr_path": OUTPUT_PATH,
        "resources": {
            "node_count": 1,
        },
        "attributes": {
            "duration": 300,
            "queue_name": QUEUE,
            "account": ACCOUNT,
            "custom_attributes": {"filesystems": "eagle"},
        },
    }
    response = requests.post(url, json=data, headers=HEADERS)
    return assert_status("Submit job", response, expected=200)


def cancel_job(job_id: str) -> bool:
    url = f"{BASE_URL}/compute/cancel/{RESOURCE_ID}/{job_id}"
    response = requests.delete(url, headers=HEADERS)
    if response.status_code == 204:
        print(f"  [OK]   Cancel job {job_id} -> HTTP 204 (Cancelled)")
        return True
    data = assert_status(f"Cancel job {job_id}", response, expected=204)
    return False


def get_job_status(job_id: str, historical: bool = False) -> dict:
    flag = "true" if historical else "false"
    url = f"{BASE_URL}/compute/status/{RESOURCE_ID}/{job_id}?historical={flag}"
    response = requests.get(url, headers=HEADERS)
    return assert_status(f"Get job status {job_id}", response, expected=200)


# ── Test ───────────────────────────────────────────────────────────────────────

def test_submit_and_cancel() -> bool:
    section("TEST: Job submission + cancellation")
    try:
        commands = "\necho 'Starting job'\nsleep 300\necho 'Done'\n"
        submit_data = submit_job(commands, name="TEST_CANCEL")
        job_id = str(submit_data.get("job_id") or submit_data.get("id") or "")
        if not job_id:
            print(f"  [FAIL] No job_id in submit response: {submit_data}")
            return False

        print(f"  [INFO] Waiting 5s before cancelling...")
        time.sleep(5)

        cancelled = cancel_job(job_id)
        if not cancelled:
            return False

        print(f"  [INFO] Polling job until it reaches a terminal state...")
        final_data = wait_for_job(RESOURCE_ID, job_id)
        final_state = extract_job_state(final_data)
        print(f"  [INFO] Final job state: {final_state}")

        if final_state == JobState.CANCELED.value:
            return True
        else:
            print(f"  [FAIL] Unexpected final state after cancel: {final_state}")
            return False

    except SystemExit:
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\nJob Cancel Test Suite")
    print(f"  BASE_URL    : {BASE_URL}")
    print(f"  RESOURCE_ID : {RESOURCE_ID}")
    print(f"  QUEUE       : {QUEUE}")
    print(f"  ACCOUNT     : {ACCOUNT}")
    print(f"  OUTPUT_PATH : {OUTPUT_PATH}")

    record("submit_and_cancel", test_submit_and_cancel())

    result_summary(passed, failed)


if __name__ == "__main__":
    main()
