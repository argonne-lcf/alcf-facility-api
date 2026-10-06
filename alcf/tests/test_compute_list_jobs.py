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

def list_jobs(historical: bool = False, limit: int = 10, offset: int = 0, filters: dict | None = None) -> list:
    url = f"{BASE_URL}/compute/status/{RESOURCE_ID}"
    params = {
        "historical": "true" if historical else "false",
        "limit": limit,
        "offset": offset,
    }
    response = requests.post(url, params=params, json=filters or {}, headers=HEADERS)
    data = assert_status("list jobs", response, expected=200)
    return data if isinstance(data, list) else data.get("items") or data.get("jobs") or []


def get_job_state(job: dict) -> str:
    status = job.get("status") or {}
    if isinstance(status, dict):
        return (status.get("state") or "").lower()
    return (status or "").lower()


def get_job_queue(job: dict) -> str:
    return (job.get("job_spec") or {}).get("attributes", {}).get("queue_name") or ""


def get_job_account(job: dict) -> str:
    return (job.get("job_spec") or {}).get("attributes", {}).get("account") or ""


def get_job_id(job: dict) -> str:
    return str(job.get("id") or job.get("job_id") or "")


def assert_jobs_not_empty(jobs: list, label: str) -> bool:
    if not jobs:
        print(f"  [FAIL] {label}: expected at least one job, got empty list")
        return False
    return True


def assert_all_jobs_have_valid_structure(jobs: list) -> bool:
    for job in jobs:
        if not get_job_id(job):
            print(f"  [FAIL] Job missing 'id' field: {job}")
            return False
        if not get_job_state(job):
            print(f"  [FAIL] Job missing 'status.state' field: {job}")
            return False
    return True


def assert_all_states_in(jobs: list, allowed_states: list[str]) -> bool:
    allowed = {s.lower() for s in allowed_states}
    for job in jobs:
        state = get_job_state(job)
        if state not in allowed:
            print(f"  [FAIL] Job {get_job_id(job)} has state '{state}', expected one of {allowed_states}")
            return False
    return True


def assert_all_queues_equal(jobs: list, expected_queue: str) -> bool:
    for job in jobs:
        queue = get_job_queue(job)
        if queue != expected_queue:
            print(f"  [FAIL] Job {get_job_id(job)} has queue '{queue}', expected '{expected_queue}'")
            return False
    return True


def assert_all_accounts_equal(jobs: list, expected_account: str) -> bool:
    for job in jobs:
        account = get_job_account(job)
        if account != expected_account:
            print(f"  [FAIL] Job {get_job_id(job)} has account '{account}', expected '{expected_account}'")
            return False
    return True


def assert_returned_ids_match(jobs: list, requested_ids: list[str]) -> bool:
    returned_ids = {get_job_id(j) for j in jobs}
    requested_set = set(requested_ids)
    extra = returned_ids - requested_set
    missing = requested_set - returned_ids
    ok = True
    if extra:
        print(f"  [FAIL] Response contained unexpected job IDs: {extra}")
        ok = False
    if missing:
        print(f"  [WARN] Some requested job IDs were not returned: {missing}")
    return ok


def assert_pages_disjoint(page1: list, page2: list) -> bool:
    ids1 = {get_job_id(j) for j in page1}
    ids2 = {get_job_id(j) for j in page2}
    overlap = ids1 & ids2
    if overlap:
        print(f"  [FAIL] Pagination overlap: same job IDs appear on both pages: {overlap}")
        return False
    return True


def assert_page_size_lte(jobs: list, limit: int) -> bool:
    if len(jobs) > limit:
        print(f"  [FAIL] Expected at most {limit} jobs, got {len(jobs)}")
        return False
    return True


# ── Test functions ─────────────────────────────────────────────────────────────

def test_list_jobs_no_filter() -> bool:
    section("TEST: list jobs (no filter)")
    try:
        jobs = list_jobs(historical=False)
        ok = assert_jobs_not_empty(jobs, "no-filter active jobs")
        ok = assert_all_jobs_have_valid_structure(jobs) and ok
        return ok
    except SystemExit:
        return False


def test_list_jobs_historical_no_filter() -> bool:
    section("TEST: list jobs historical (no filter)")
    try:
        jobs = list_jobs(historical=True)
        ok = assert_jobs_not_empty(jobs, "no-filter historical jobs")
        ok = assert_all_jobs_have_valid_structure(jobs) and ok
        return ok
    except SystemExit:
        return False


def test_list_jobs_filter_by_state() -> bool:
    section("TEST: list jobs with filter: states")
    allowed = ["completed", "failed"]
    try:
        jobs = list_jobs(historical=True, filters={"states": allowed})
        ok = assert_all_jobs_have_valid_structure(jobs)
        ok = assert_all_states_in(jobs, allowed) and ok
        if ok:
            print(f"  [OK]  All {len(jobs)} jobs have state in {allowed}")
        return ok
    except SystemExit:
        return False


def test_list_jobs_filter_by_owner() -> bool:
    section("TEST: list jobs with filter: owner")
    try:
        owner = get_env("COMPUTE_OWNER", required=False)
        if not owner:
            print("  [SKIP] COMPUTE_OWNER not set, skipping owner filter test")
            return True
        jobs = list_jobs(historical=True, filters={"owner": owner})
        ok = assert_all_jobs_have_valid_structure(jobs)
        if ok:
            print(f"  [OK]  All {len(jobs)} jobs passed structure check for owner '{owner}'")
        return ok
    except SystemExit:
        return False


def test_list_jobs_filter_by_queue() -> bool:
    section("TEST: list jobs with filter: queue")
    try:
        queue = get_env("COMPUTE_QUEUE", required=False)
        if not queue:
            print("  [SKIP] COMPUTE_QUEUE not set, skipping queue filter test")
            return True
        jobs = list_jobs(historical=True, filters={"queue": queue})
        ok = assert_all_jobs_have_valid_structure(jobs)
        ok = assert_all_queues_equal(jobs, queue) and ok
        if ok:
            print(f"  [OK]  All {len(jobs)} jobs have queue '{queue}'")
        return ok
    except SystemExit:
        return False


def test_list_jobs_filter_by_accounting_id() -> bool:
    section("TEST: list jobs with filter: accountingId")
    try:
        jobs = list_jobs(historical=True, filters={"accountingId": ACCOUNT})
        ok = assert_all_jobs_have_valid_structure(jobs)
        ok = assert_all_accounts_equal(jobs, ACCOUNT) and ok
        if ok:
            print(f"  [OK]  All {len(jobs)} jobs have account '{ACCOUNT}'")
        return ok
    except SystemExit:
        return False


def test_list_jobs_combined_filters() -> bool:
    section("TEST: list jobs with combined filters: states + accountingId")
    allowed_states = ["completed"]
    try:
        jobs = list_jobs(historical=True, filters={"states": allowed_states, "accountingId": ACCOUNT})
        ok = assert_all_jobs_have_valid_structure(jobs)
        ok = assert_all_states_in(jobs, allowed_states) and ok
        ok = assert_all_accounts_equal(jobs, ACCOUNT) and ok
        if ok:
            print(f"  [OK]  All {len(jobs)} jobs have state in {allowed_states} and account '{ACCOUNT}'")
        return ok
    except SystemExit:
        return False


def test_list_jobs_pagination() -> bool:
    section("TEST: list jobs pagination (limit + offset)")
    limit = 5
    try:
        page1 = list_jobs(historical=True, limit=limit, offset=0)
        page2 = list_jobs(historical=True, limit=limit, offset=limit)
        ok = assert_page_size_lte(page1, limit)
        ok = assert_page_size_lte(page2, limit) and ok
        ok = assert_pages_disjoint(page1, page2) and ok
        if ok:
            print(f"  [OK]  Pages are disjoint: {len(page1)} + {len(page2)} unique jobs")
        return ok
    except SystemExit:
        return False


def test_list_jobs_filter_by_job_ids() -> bool:
    section("TEST: list jobs with filter: jobIds (from first page)")
    try:
        seed_jobs = list_jobs(historical=True, limit=3, offset=0)
        if not seed_jobs:
            print("  [SKIP] No jobs returned to use as jobIds filter input")
            return True
        job_ids = [get_job_id(j) for j in seed_jobs if get_job_id(j)]
        if not job_ids:
            print("  [SKIP] Could not extract job IDs from response")
            return True
        print(f"  [INFO] Filtering by jobIds: {job_ids}")
        jobs = list_jobs(historical=True, filters={"jobIds": job_ids})
        ok = assert_all_jobs_have_valid_structure(jobs)
        ok = assert_returned_ids_match(jobs, job_ids) and ok
        if ok:
            print(f"  [OK]  Returned {len(jobs)} jobs exactly matching requested IDs")
        return ok
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
