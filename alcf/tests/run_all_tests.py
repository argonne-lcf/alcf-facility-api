# 
# AI generated
#

import sys
import argparse
import importlib
import traceback
from dotenv import load_dotenv

load_dotenv(override=True)

SUITES = [
    ("account",    "test_account"),
    ("filesystem", "test_filesystem"),
    ("cancel",     "test_job_cancel"),
    ("stdout",     "test_job_stdout"),
]


def run_suite(module_name: str) -> bool:
    try:
        mod = importlib.import_module(module_name)
        mod.main()
        return True
    except SystemExit as e:
        if e.code == 0:
            return True
        print(f"\n[ORCHESTRATOR] Suite '{module_name}' exited with code {e.code}")
        return False
    except Exception:
        print(f"\n[ORCHESTRATOR] Suite '{module_name}' raised an exception:")
        traceback.print_exc()
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ALCF Facility API test suites")
    parser.add_argument("--account",    action="store_true", help="Run account tests")
    parser.add_argument("--filesystem", action="store_true", help="Run filesystem tests")
    parser.add_argument("--cancel",     action="store_true", help="Run job cancel tests")
    parser.add_argument("--stdout",     action="store_true", help="Run job stdout tests")
    args = parser.parse_args()

    run_all = not any([args.account, args.filesystem, args.cancel, args.stdout])

    selected = [
        (flag, mod)
        for flag, mod in SUITES
        if run_all or getattr(args, flag, False)
    ]

    print("\n" + "=" * 60)
    print("  ALCF Facility API — Integration Test Runner")
    print("=" * 60)
    print(f"  Suites to run: {[mod for _, mod in selected]}\n")

    overall_passed: list[str] = []
    overall_failed: list[str] = []

    for flag, mod in selected:
        print(f"\n{'#' * 60}")
        print(f"  Running suite: {mod}")
        print(f"{'#' * 60}")
        ok = run_suite(mod)
        (overall_passed if ok else overall_failed).append(mod)

    print(f"\n{'=' * 60}")
    print("  OVERALL RESULT")
    print("=" * 60)
    for name in overall_passed:
        print(f"  [PASS] {name}")
    for name in overall_failed:
        print(f"  [FAIL] {name}")
    total = len(overall_passed) + len(overall_failed)
    print(f"\n  {len(overall_passed)}/{total} suites passed")

    if overall_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
