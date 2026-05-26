# 
# AI generated
#

import sys
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from utils import (
    get_env,
    get_headers,
    get_base_url,
    assert_status,
    wait_for_job,
    wait_for_task,
    extract_job_state,
    section,
    result_summary,
    JobState,
    Task,
)

BASE_URL = get_base_url()
HEADERS = get_headers()
COMPUTE_RESOURCE_ID = get_env("COMPUTE_RESOURCE_ID")
FILESYSTEM_RESOURCE_ID = get_env("FILESYSTEM_RESOURCE_ID")
OUTPUT_PATH = get_env("COMPUTE_OUTPUT_PATH").rstrip("/")
ACCOUNT = get_env("COMPUTE_ACCOUNT")
QUEUE = get_env("COMPUTE_QUEUE")

SENTINEL = "ALCF_TEST_STDOUT_OK_12345"

passed: list[str] = []
failed: list[str] = []


def record(name: str, ok: bool) -> None:
    (passed if ok else failed).append(name)


# ── Helpers ────────────────────────────────────────────────────────────────────

def submit_job() -> dict:
    commands = f"""
echo 'Job starting'
echo '{SENTINEL}'
echo 'Job done'
"""
    url = f"{BASE_URL}/compute/job/{COMPUTE_RESOURCE_ID}"
    data = {
        "executable": "/bin/bash",
        "arguments": ["-lc", commands],
        "name": "TEST_STDOUT",
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


def get_job_stdout_path(job_id: str) -> str:
    return f"{OUTPUT_PATH}/{job_id}.OU"


def view_file(path: str, size: int = 4096, offset: int = 0) -> Task:
    url = f"{BASE_URL}/filesystem/view/{FILESYSTEM_RESOURCE_ID}"
    response = requests.get(url, params={"path": path, "size": size, "offset": offset}, headers=HEADERS)
    data = assert_status(f"filesystem/view {path}", response, expected=200)
    task_id = data.get("task_id")
    if not task_id:
        print(f"  [FAIL] No task_id in view response: {data}")
        sys.exit(1)
    print(f"  [INFO] task_id = {task_id}")
    return wait_for_task(task_id)


def head_file(path: str, lines: int = 20) -> Task:
    url = f"{BASE_URL}/filesystem/head/{FILESYSTEM_RESOURCE_ID}"
    response = requests.get(url, params={"path": path, "lines": lines}, headers=HEADERS)
    data = assert_status(f"filesystem/head {path}", response, expected=200)
    task_id = data.get("task_id")
    if not task_id:
        print(f"  [FAIL] No task_id in head response: {data}")
        sys.exit(1)
    print(f"  [INFO] task_id = {task_id}")
    return wait_for_task(task_id)


# ── Test ───────────────────────────────────────────────────────────────────────

def test_submit_and_read_stdout() -> bool:
    section("TEST: Job submission + stdout file verification")
    try:
        submit_data = submit_job()
        job_id = str(submit_data.get("job_id") or submit_data.get("id") or "")
        if not job_id:
            print(f"  [FAIL] No job_id in submit response: {submit_data}")
            return False
        print(f"  [INFO] Submitted job_id = {job_id}")

        print("  [INFO] Waiting for job to complete...")
        final_data = wait_for_job(COMPUTE_RESOURCE_ID, job_id)
        final_state = extract_job_state(final_data)
        print(f"  [INFO] Final job state: {final_state}")

        if final_state in (JobState.FAILED.value, JobState.CANCELED.value):
            print(f"  [WARN] Job ended in state {final_state}; will still attempt to read stdout.")

        stdout_path = get_job_stdout_path(job_id)
        print(f"  [INFO] Expected stdout file: {stdout_path}")

        section("  Reading stdout via filesystem/head")
        head_result = head_file(stdout_path, lines=50)
        content = head_result.result or {}

        if SENTINEL in str(content):
            print(f"  [OK]   Sentinel string '{SENTINEL}' found in stdout.")
            return True

        section("  Fallback: reading stdout via filesystem/view")
        view_result = view_file(stdout_path, size=8192, offset=0)
        content = view_result.result or {}

        if SENTINEL in str(content):
            print(f"  [OK]   Sentinel string '{SENTINEL}' found in stdout via view.")
            return True

        print(f"  [FAIL] Sentinel string '{SENTINEL}' NOT found in stdout file.")
        return False

    except SystemExit:
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\nJob Stdout Test Suite")
    print(f"  BASE_URL               : {BASE_URL}")
    print(f"  COMPUTE_RESOURCE_ID    : {COMPUTE_RESOURCE_ID}")
    print(f"  FILESYSTEM_RESOURCE_ID : {FILESYSTEM_RESOURCE_ID}")
    print(f"  QUEUE                  : {QUEUE}")
    print(f"  ACCOUNT                : {ACCOUNT}")
    print(f"  OUTPUT_PATH            : {OUTPUT_PATH}")
    print(f"  SENTINEL               : {SENTINEL}")

    record("submit_and_read_stdout", test_submit_and_read_stdout())

    result_summary(passed, failed)


if __name__ == "__main__":
    main()
