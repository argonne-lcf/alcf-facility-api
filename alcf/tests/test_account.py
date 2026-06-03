# 
# AI generated
#

import sys
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from utils import (
    get_headers,
    get_base_url,
    assert_status,
    section,
    result_summary,
)

BASE_URL = get_base_url()
HEADERS = get_headers()

passed: list[str] = []
failed: list[str] = []


def record(name: str, ok: bool) -> None:
    (passed if ok else failed).append(name)


# ── Helpers ────────────────────────────────────────────────────────────────────

def account_url(path: str) -> str:
    return f"{BASE_URL}/account/{path}"


# ── Test functions ─────────────────────────────────────────────────────────────

def test_get_capabilities() -> bool:
    section("TEST: get capabilities")
    try:
        url = account_url("capabilities")
        response = requests.get(url, params={"limit": 100, "offset": 0}, headers=HEADERS)
        assert_status("get capabilities", response, expected=200)
        return True
    except SystemExit:
        return False


def test_get_capability() -> bool:
    section("TEST: get capability by id")
    try:
        url = account_url("capabilities")
        response = requests.get(url, params={"limit": 100, "offset": 0}, headers=HEADERS)
        capabilities = assert_status("list capabilities", response, expected=200)
        if not capabilities:
            print("  [SKIP] No capabilities available to test single fetch")
            return True
        capability_id = capabilities[0]["id"]
        url = account_url(f"capabilities/{capability_id}")
        response = requests.get(url, headers=HEADERS)
        assert_status(f"get capability {capability_id}", response, expected=200)
        return True
    except SystemExit:
        return False


def test_get_projects() -> bool:
    section("TEST: get projects")
    try:
        url = account_url("projects")
        response = requests.get(url, headers=HEADERS)
        assert_status("get projects", response, expected=200)
        return True
    except SystemExit:
        return False


def test_get_project() -> bool:
    section("TEST: get project by id")
    try:
        url = account_url("projects")
        response = requests.get(url, headers=HEADERS)
        projects = assert_status("list projects", response, expected=200)
        if not projects:
            print("  [SKIP] No projects available to test single fetch")
            return True
        project_id = projects[0]["id"]
        url = account_url(f"projects/{project_id}")
        response = requests.get(url, headers=HEADERS)
        assert_status(f"get project {project_id}", response, expected=200)
        return True
    except SystemExit:
        return False


def test_get_project_allocations() -> bool:
    section("TEST: get project allocations")
    try:
        url = account_url("projects")
        response = requests.get(url, headers=HEADERS)
        projects = assert_status("list projects", response, expected=200)
        if not projects:
            print("  [SKIP] No projects available to test project allocations")
            return True
        project_id = projects[0]["id"]
        url = account_url(f"projects/{project_id}/project_allocations")
        response = requests.get(url, headers=HEADERS)
        assert_status(f"get project allocations for {project_id}", response, expected=200)
        return True
    except SystemExit:
        return False


def test_get_project_allocation() -> bool:
    section("TEST: get project allocation by id")
    try:
        url = account_url("projects")
        response = requests.get(url, headers=HEADERS)
        projects = assert_status("list projects", response, expected=200)
        if not projects:
            print("  [SKIP] No projects available to test project allocation fetch")
            return True
        project_id = projects[0]["id"]
        url = account_url(f"projects/{project_id}/project_allocations")
        response = requests.get(url, headers=HEADERS)
        allocations = assert_status("list project allocations", response, expected=200)
        if not allocations:
            print("  [SKIP] No project allocations available to test single fetch")
            return True
        allocation_id = allocations[0]["id"]
        url = account_url(f"projects/{project_id}/project_allocations/{allocation_id}")
        response = requests.get(url, headers=HEADERS)
        assert_status(f"get project allocation {allocation_id}", response, expected=200)
        return True
    except SystemExit:
        return False


def test_get_user_allocations() -> bool:
    section("TEST: get user allocations")
    try:
        url = account_url("projects")
        response = requests.get(url, headers=HEADERS)
        projects = assert_status("list projects", response, expected=200)
        if not projects:
            print("  [SKIP] No projects available to test user allocations")
            return True
        project_id = projects[0]["id"]
        url = account_url(f"projects/{project_id}/project_allocations")
        response = requests.get(url, headers=HEADERS)
        allocations = assert_status("list project allocations", response, expected=200)
        if not allocations:
            print("  [SKIP] No project allocations available to test user allocations")
            return True
        allocation_id = allocations[0]["id"]
        url = account_url(f"projects/{project_id}/project_allocations/{allocation_id}/user_allocations")
        response = requests.get(url, headers=HEADERS)
        assert_status(f"get user allocations for {allocation_id}", response, expected=200)
        return True
    except SystemExit:
        return False


def test_get_user_allocation() -> bool:
    section("TEST: get user allocation by id")
    try:
        url = account_url("projects")
        response = requests.get(url, headers=HEADERS)
        projects = assert_status("list projects", response, expected=200)
        if not projects:
            print("  [SKIP] No projects available to test user allocation fetch")
            return True
        project_id = projects[0]["id"]
        url = account_url(f"projects/{project_id}/project_allocations")
        response = requests.get(url, headers=HEADERS)
        allocations = assert_status("list project allocations", response, expected=200)
        if not allocations:
            print("  [SKIP] No project allocations available to test user allocation fetch")
            return True
        allocation_id = allocations[0]["id"]
        url = account_url(f"projects/{project_id}/project_allocations/{allocation_id}/user_allocations")
        response = requests.get(url, headers=HEADERS)
        user_allocations = assert_status("list user allocations", response, expected=200)
        if not user_allocations:
            print("  [SKIP] No user allocations available to test single fetch")
            return True
        user_allocation_id = user_allocations[0]["id"]
        url = account_url(f"projects/{project_id}/project_allocations/{allocation_id}/user_allocations/{user_allocation_id}")
        response = requests.get(url, headers=HEADERS)
        assert_status(f"get user allocation {user_allocation_id}", response, expected=200)
        return True
    except SystemExit:
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\nAccount Test Suite")
    print(f"  BASE_URL : {BASE_URL}")

    record("get_capabilities",      test_get_capabilities())
    record("get_capability",        test_get_capability())
    record("get_projects",          test_get_projects())
    record("get_project",           test_get_project())
    record("get_project_allocations", test_get_project_allocations())
    record("get_project_allocation",  test_get_project_allocation())
    record("get_user_allocations",  test_get_user_allocations())
    record("get_user_allocation",   test_get_user_allocation())

    result_summary(passed, failed)


if __name__ == "__main__":
    main()
