# 
# AI generated
#

import sys
import os
import requests
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv(override=True)

from utils import (
    get_env,
    get_headers,
    get_base_url,
    assert_status,
    wait_for_task,
    wait_for_job,
    section,
    result_summary,
)

BASE_URL = get_base_url()
HEADERS = get_headers()
FILESYSTEM_RESOURCE_ID = get_env("FILESYSTEM_RESOURCE_ID")
COMPUTE_RESOURCE_ID = get_env("COMPUTE_RESOURCE_ID")
ACCOUNT = get_env("COMPUTE_ACCOUNT")
QUEUE = get_env("COMPUTE_QUEUE")
BASE_PATH = get_env("FILESYSTEM_BASE_PATH").rstrip("/")

TEST_DIR = f"{BASE_PATH}/alcf_test_run-{str(uuid4())[:8]}"
TEST_SUBDIR = f"{TEST_DIR}/subdir"
TEST_SUBDIR_FILE = f"{TEST_SUBDIR}/test.txt"
TEST_JSON_FILE = f"{TEST_DIR}/data.json"
TEST_TEXT_FILE = f"{TEST_DIR}/notes.txt"

passed: list[str] = []
failed: list[str] = []


def record(name: str, ok: bool) -> None:
    (passed if ok else failed).append(name)


# ── Helpers ────────────────────────────────────────────────────────────────────

def fs_url(op: str) -> str:
    return f"{BASE_URL}/filesystem/{op}/{FILESYSTEM_RESOURCE_ID}"


def submit_and_wait(label: str, method: str, op: str, payload: dict | None = None, params: dict | None = None, expected_status: int = 200) -> dict:
    url = fs_url(op)
    if method == "GET":
        response = requests.get(url, params=params, headers=HEADERS)
    elif method == "POST":
        response = requests.post(url, json=payload, headers=HEADERS)
    elif method == "PUT":
        response = requests.put(url, json=payload, headers=HEADERS)
    elif method == "DELETE":
        response = requests.delete(url, params=params, headers=HEADERS)
    else:
        raise ValueError(f"Unsupported method: {method}")

    data = assert_status(label, response, expected=expected_status)
    task_id = data.get("task_id")
    if not task_id:
        print(f"  [FAIL] {label}: no task_id in response")
        print(data)
        sys.exit(1)
    print(f"  [INFO] task_id = {task_id}")
    return wait_for_task(task_id)


# ── Test functions ─────────────────────────────────────────────────────────────

def test_mkdir() -> bool:
    section("TEST: mkdir")
    try:
        submit_and_wait(
            "mkdir (create test directory)",
            "POST",
            "mkdir",
            payload={"path": TEST_DIR, "parent": True},
            expected_status=201,
        )
        return True
    except SystemExit:
        return False


def test_populate() -> bool:
    section("TEST: populate (submit job to create files)")
    username = os.path.basename(BASE_PATH)
    commands = f"""
        mkdir -p {TEST_SUBDIR}
        echo "Hello from the test suite" > {TEST_SUBDIR_FILE}
        echo '{{"name": "alcf_test", "version": 1, "ok": true}}' > {TEST_JSON_FILE}
        echo "Short note for testing." > {TEST_TEXT_FILE}
    """
    url = f"{BASE_URL}/compute/job/{COMPUTE_RESOURCE_ID}"
    data = {
        "executable": "/bin/bash",
        "arguments": ["-lc", commands],
        "name": "FILESYSTEM_TEST_POPULATE",
        "stdout_path": TEST_DIR,
        "stderr_path": TEST_DIR,
        "resources": {
            "node_count": 1,
        },
        "attributes": {
            "duration": 300,
            "queue_name": QUEUE,
            "account": ACCOUNT,
            "custom_attributes": {"filesystems": "home"},
        },
    }
    try:
        response = requests.post(url, json=data, headers=HEADERS)
        submit_data = assert_status("Submit populate job", response, expected=200)
        job_id = str(submit_data.get("job_id") or submit_data.get("id") or "")
        if not job_id:
            print(f"  [FAIL] No job_id in submit response: {submit_data}")
            return False
        print(f"  [INFO] Submitted job_id = {job_id}")
        print("  [INFO] Waiting for populate job to complete...")
        wait_for_job(COMPUTE_RESOURCE_ID, job_id)
        return True
    except SystemExit:
        return False


def test_ls_dir() -> bool:
    section("TEST: ls (list test directory)")
    try:
        submit_and_wait(
            "ls (list test directory)",
            "GET",
            "ls",
            params={"path": TEST_DIR},
        )
        return True
    except SystemExit:
        return False


def test_chmod() -> bool:
    section("TEST: chmod")
    try:
        submit_and_wait(
            "chmod (set notes.txt permissions to 644)",
            "PUT",
            "chmod",
            payload={"path": TEST_TEXT_FILE, "mode": "644"},
        )
        submit_and_wait(
            "chmod (set subdir permissions to 755)",
            "PUT",
            "chmod",
            payload={"path": TEST_SUBDIR, "mode": "755"},
        )
        return True
    except SystemExit:
        return False


def test_chown() -> bool:
    section("TEST: chown")
    username = os.path.basename(BASE_PATH)
    try:
        submit_and_wait(
            "chown (set notes.txt owner)",
            "PUT",
            "chown",
            payload={"path": TEST_TEXT_FILE, "owner": username, "group": "users"},
        )
        submit_and_wait(
            "chown (set subdir owner)",
            "PUT",
            "chown",
            payload={"path": TEST_SUBDIR, "owner": username, "group": "users"},
        )
        return True
    except SystemExit:
        return False


def test_head() -> bool:
    section("TEST: head")
    try:
        submit_and_wait(
            "head (read first lines of notes.txt)",
            "GET",
            "head",
            params={"path": TEST_TEXT_FILE, "lines": 5},
        )
        return True
    except SystemExit:
        return False


def test_view() -> bool:
    section("TEST: view")
    try:
        submit_and_wait(
            "view (read bytes from notes.txt)",
            "GET",
            "view",
            params={"path": TEST_TEXT_FILE, "size": 100, "offset": 0},
        )
        return True
    except SystemExit:
        return False


def test_tail() -> bool:
    section("TEST: tail")
    try:
        submit_and_wait(
            "tail (read last lines of notes.txt)",
            "GET",
            "tail",
            params={"path": TEST_TEXT_FILE, "lines": 5},
        )
        return True
    except SystemExit:
        return False


def test_checksum() -> bool:
    section("TEST: checksum")
    try:
        submit_and_wait(
            "checksum (SHA-256 of notes.txt)",
            "GET",
            "checksum",
            params={"path": TEST_TEXT_FILE},
        )
        return True
    except SystemExit:
        return False


def test_file() -> bool:
    section("TEST: file")
    try:
        submit_and_wait(
            "file (type of notes.txt)",
            "GET",
            "file",
            params={"path": TEST_TEXT_FILE},
        )
        submit_and_wait(
            "file (type of subdir)",
            "GET",
            "file",
            params={"path": TEST_SUBDIR},
        )
        return True
    except SystemExit:
        return False


def test_rm() -> bool:
    section("TEST: rm")
    try:
        submit_and_wait(
            "rm (remove test directory)",
            "DELETE",
            "rm",
            params={"path": TEST_DIR},
        )
        return True
    except SystemExit:
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\nFilesystem Test Suite")
    print(f"  BASE_URL               : {BASE_URL}")
    print(f"  FILESYSTEM_RESOURCE_ID : {FILESYSTEM_RESOURCE_ID}")
    print(f"  COMPUTE_RESOURCE_ID    : {COMPUTE_RESOURCE_ID}")
    print(f"  BASE_PATH              : {BASE_PATH}")
    print(f"  TEST_DIR               : {TEST_DIR}")
    print(f"  TEST_SUBDIR            : {TEST_SUBDIR}")
    print(f"  TEST_TEXT_FILE         : {TEST_TEXT_FILE}")
    print(f"  TEST_JSON_FILE         : {TEST_JSON_FILE}")

    record("mkdir", test_mkdir())
    record("populate", test_populate())
    record("ls", test_ls_dir())
    record("chmod", test_chmod())
    record("chown", test_chown())
    record("head", test_head())
    record("tail", test_tail())
    record("view", test_view())
    record("checksum", test_checksum())
    record("file", test_file())
    record("rm", test_rm())

    result_summary(passed, failed)


if __name__ == "__main__":
    main()
