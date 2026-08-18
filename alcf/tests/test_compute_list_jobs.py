# 
# AI generated
#

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from utils import (
    get_env,
    get_headers,
    get_base_url,
    assert_status,
    section,
    result_summary,
)

BASE_URL = get_base_url()
HEADERS = get_headers()
RESOURCE_ID = get_env("COMPUTE_RESOURCE_ID")
ACCOUNT = get_env("COMPUTE_ACCOUNT")

passed: list[str] = []
failed: list[str] = []


def record(name: str, ok: bool) -> None:
    (passed if ok else failed).append(name)


# ── Helpers ────────────────────────────────────────────────────────────────────

def list_jobs(historical: bool = False, limit: int = 10, offset: int = 0, filters: dict | None = None) -> dict:
    url = f"{BASE_URL}/compute/status/{RESOURCE_ID}"
    params = {
        "historical": "true" if historical else "false",
        "limit": limit,
        "offset": offset,
    }
    response = requests.post(url, params=params, json=filters or {}, headers=HEADERS)
    return assert_status("list jobs", response, expected=200)


# ── Test functions ─────────────────────────────────────────────────────────────

def test_list_jobs_no_filter() -> bool:
    section("TEST: list jobs (no filter)")
    try:
        list_jobs(historical=False)
        return True
    except SystemExit:
        return False


def test_list_jobs_historical_no_filter() -> bool:
    section("TEST: list jobs historical (no filter)")
    try:
        list_jobs(historical=True)
        return True
    except SystemExit:
        return False


def test_list_jobs_filter_by_state() -> bool:
    section("TEST: list jobs with filter: states")
    try:
        list_jobs(historical=True, filters={"states": ["completed", "failed"]})
        return True
    except SystemExit:
        return False


def test_list_jobs_filter_by_owner() -> bool:
    section("TEST: list jobs with filter: owner")
    try:
        owner = get_env("COMPUTE_OWNER", required=False)
        if not owner:
            print("  [SKIP] COMPUTE_OWNER not set, skipping owner filter test")
            return True
        list_jobs(historical=True, filters={"owner": owner})
        return True
    except SystemExit:
        return False


def test_list_jobs_filter_by_queue() -> bool:
    section("TEST: list jobs with filter: queue")
    try:
        queue = get_env("COMPUTE_QUEUE", required=False)
        if not queue:
            print("  [SKIP] COMPUTE_QUEUE not set, skipping queue filter test")
            return True
        list_jobs(historical=True, filters={"queue": queue})
        return True
    except SystemExit:
        return False


def test_list_jobs_filter_by_accounting_id() -> bool:
    section("TEST: list jobs with filter: accountingId")
    try:
        list_jobs(historical=True, filters={"accountingId": ACCOUNT})
        return True
    except SystemExit:
        return False


def test_list_jobs_combined_filters() -> bool:
    section("TEST: list jobs with combined filters: states + accountingId")
    try:
        list_jobs(historical=True, filters={"states": ["completed"], "accountingId": ACCOUNT})
        return True
    except SystemExit:
        return False


def test_list_jobs_pagination() -> bool:
    section("TEST: list jobs pagination (limit + offset)")
    try:
        list_jobs(historical=True, limit=5, offset=0)
        list_jobs(historical=True, limit=5, offset=5)
        return True
    except SystemExit:
        return False


def test_list_jobs_filter_by_job_ids() -> bool:
    section("TEST: list jobs with filter: jobIds (from first page)")
    try:
        data = list_jobs(historical=True, limit=3, offset=0)
        items = data if isinstance(data, list) else data.get("items") or data.get("jobs") or []
        if not items:
            print("  [SKIP] No jobs returned to use as jobIds filter input")
            return True
        job_ids = [str(item.get("job_id") or item.get("id") or "") for item in items[:3]]
        job_ids = [j for j in job_ids if j]
        if not job_ids:
            print("  [SKIP] Could not extract job IDs from response")
            return True
        print(f"  [INFO] Filtering by jobIds: {job_ids}")
        list_jobs(historical=True, filters={"jobIds": job_ids})
        return True
    except SystemExit:
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\nCompute List Jobs Test Suite")
    print(f"  BASE_URL    : {BASE_URL}")
    print(f"  RESOURCE_ID : {RESOURCE_ID}")
    print(f"  ACCOUNT     : {ACCOUNT}")

    record("list_jobs_no_filter",             test_list_jobs_no_filter())
    record("list_jobs_historical_no_filter",  test_list_jobs_historical_no_filter())
    record("list_jobs_filter_by_state",       test_list_jobs_filter_by_state())
    record("list_jobs_filter_by_owner",       test_list_jobs_filter_by_owner())
    record("list_jobs_filter_by_queue",       test_list_jobs_filter_by_queue())
    record("list_jobs_filter_by_accounting_id", test_list_jobs_filter_by_accounting_id())
    record("list_jobs_combined_filters",      test_list_jobs_combined_filters())
    record("list_jobs_pagination",            test_list_jobs_pagination())
    record("list_jobs_filter_by_job_ids",     test_list_jobs_filter_by_job_ids())

    result_summary(passed, failed)


if __name__ == "__main__":
    main()
