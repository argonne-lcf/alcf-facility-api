import sys
import argparse
import requests
from dotenv import load_dotenv

from utils import (
    get_env,
    get_headers,
    get_base_url,
    assert_status,
    wait_for_job,
    wait_for_task,
    extract_job_state,
    set_current_test,
    section,
    result_summary,
    JobState,
    Task,
    filesystem_request,
)

from job_input_cases import CASES

BASE_URL = None
HEADERS = None
COMPUTE_RESOURCE_ID = None
FILESYSTEM_RESOURCE_ID = None
OUTPUT_PATH = None
ACCOUNT = None
QUEUE = None
FILESYSTEM = None

passed: list[str] = []
failed: list[str] = []


def submit_job(commands: str) -> dict:
    url = f"{BASE_URL}/compute/job/{COMPUTE_RESOURCE_ID}"
    data = {
        "executable": "/bin/bash",
        "arguments": ["-lc", commands],
        "stdout_path": OUTPUT_PATH,
        "stderr_path": OUTPUT_PATH,
        "resources": {"node_count": 1},
        "attributes": {
            "duration": 300,
            "queue_name": QUEUE,
            "account": ACCOUNT,
            "custom_attributes": {"filesystems": FILESYSTEM},
        },
    }
    response = requests.post(url, json=data, headers=HEADERS)
    return assert_status("Submit job", response, expected=200)


def view_file(path: str, size: int = 8192, offset: int = 0) -> Task:
    url = f"{BASE_URL}/filesystem/view/{FILESYSTEM_RESOURCE_ID}"
    response = filesystem_request(
        url, HEADERS, data={"path": path, "size": size, "offset": offset}, base_url=BASE_URL
    )
    data = assert_status(f"filesystem/view {path}", response, expected=200)
    task_id = data.get("task_id")
    if not task_id:
        print(f"  [FAIL] No task_id in view response: {data}")
        sys.exit(1)
    print(f"  [INFO] task_id = {task_id}")
    return wait_for_task(task_id)


def run_case(index: int, case: dict) -> bool:
    label = f"case_{index}"
    commands = case["commands"]
    expected = case["expected"]

    section(f"TEST {index}/{len(CASES) - 1}")
    set_current_test(label)
    try:
        submit_data = submit_job(commands)
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

        stdout_path = f"{OUTPUT_PATH}/{job_id}.OU"
        print(f"  [INFO] Expected stdout file: {stdout_path}")

        view_result = view_file(stdout_path)
        result = view_result.result or {}
        content = str((result.get("output") or {}).get("content", ""))

        if expected in content:
            print(f"  [OK]   Found expected output for case {index}")
            return True
        else:
            print(f"  [FAIL] Expected output not found for case {index}.")
            print(f"  [FAIL] --- Expected ---\n{expected}")
            print(f"  [FAIL] --- Actual stdout content ---\n{content}")
            return False
    except SystemExit:
        return False
    finally:
        set_current_test(None)


def main() -> None:
    global BASE_URL, HEADERS, COMPUTE_RESOURCE_ID, FILESYSTEM_RESOURCE_ID, OUTPUT_PATH, ACCOUNT, QUEUE, FILESYSTEM
    BASE_URL = get_base_url()
    HEADERS = get_headers()
    COMPUTE_RESOURCE_ID = get_env("COMPUTE_RESOURCE_ID")
    FILESYSTEM_RESOURCE_ID = get_env("FILESYSTEM_RESOURCE_ID")
    OUTPUT_PATH = get_env("COMPUTE_OUTPUT_PATH").rstrip("/")
    ACCOUNT = get_env("COMPUTE_ACCOUNT")
    QUEUE = get_env("COMPUTE_QUEUE")
    FILESYSTEM = get_env("COMPUTE_FILESYSTEM")

    print("\nJob Inputs Test Suite")
    print(f"  BASE_URL               : {BASE_URL}")
    print(f"  COMPUTE_RESOURCE_ID    : {COMPUTE_RESOURCE_ID}")
    print(f"  FILESYSTEM_RESOURCE_ID : {FILESYSTEM_RESOURCE_ID}")
    print(f"  QUEUE                  : {QUEUE}")
    print(f"  ACCOUNT                : {ACCOUNT}")
    print(f"  OUTPUT_PATH            : {OUTPUT_PATH}")
    print(f"  Number of test cases   : {len(CASES)}")

    for index, case in enumerate(CASES):
        label = f"case_{index}"
        ok = run_case(index, case)
        (passed if ok else failed).append(label)

    result_summary(passed, failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=".env", help="Path to env file (default: .env)")
    args = parser.parse_args()
    load_dotenv(dotenv_path=".env", override=False)
    load_dotenv(dotenv_path=args.env, override=True)
    main()
