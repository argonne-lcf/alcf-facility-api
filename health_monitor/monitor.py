import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

import globus_sdk
from dotenv import load_dotenv

from httpx_calls import httpx_get, httpx_post
from slack_hook import post_to_slack

load_dotenv(override=True)

HTTP_TIMEOUT_SEC = int(os.getenv("HTTP_TIMEOUT_SEC", 10))

HOME_PATH = os.getenv("HOME_PATH")
if HOME_PATH is None:
    print("HOME_PATH must be defined.")
    sys.exit(1)

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", None)

# Authorized Globus confidential client
if ACCESS_TOKEN is None:
    CLIENT_ID = os.getenv("GLOBUS_CONFIDENTIAL_CLIENT_ID", None)
    CLIENT_SECRET = os.getenv("GLOBUS_CONFIDENTIAL_CLIENT_SECRET", None)
    if CLIENT_ID is None or CLIENT_SECRET is None:
        print("No confidential client credentials.")
        sys.exit(1)

# Access token for the IRI API
if ACCESS_TOKEN is None:
    SCOPE_CLIENT_ID = "6be511f6-a071-471f-9bc0-02a0d0836723"
    SCOPE_STRING = f"https://auth.globus.org/scopes/{SCOPE_CLIENT_ID}/filesystem"
    client = globus_sdk.ConfidentialAppAuthClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    token_response = client.oauth2_client_credentials_tokens(requested_scopes=[SCOPE_STRING])
    ACCESS_TOKEN = token_response.by_resource_server[SCOPE_CLIENT_ID]["access_token"]

# Request Headers
ANONYMOUS_HEADERS = {
    "Content-Type": "application/json"
}
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}


async def run_checks(full: bool = False) -> None:
    results = await asyncio.gather(
        check_facility(),
        check_sites(),
        check_sites_site(),
        check_status_resources(),
        check_status_resources_resource(),
        check_status_incidents(),
        check_status_events(),
        check_account_capabilities(),
        check_account_projects(),
        check_compute_status_polaris(),
        check_compute_status_crux(),
        check_filesystem_ls(),
        check_tasks(),
    )

    def with_prefix(entries):
        lines = []
        for msg in entries:
            comp = msg.split("/")[0].split(":")[0].strip()
            lines.append(f"• [{comp}] {msg}")
        return "\n".join(lines)

    failed = [msg for ok, msg in results if not ok]
    passed = [msg for ok, msg in results if ok]

    sections = []
    if failed:
        sections.append(f"❌ *Failed*\n{with_prefix(failed)}")
    if full and passed:
        sections.append(f"✅ *Healthy*\n{with_prefix(passed)}")

    if sections:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        header = f"Health Monitor @ {now}\nTotal checked: {len(results)} | failed: {len(failed)} | healthy: {len(passed)}"
        await post_to_slack(header + "\n\n" + "\n\n".join(sections))

async def check_facility():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        ANONYMOUS_HEADERS,
        "facility")


async def check_sites():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        ANONYMOUS_HEADERS,
        "facility/sites")


async def check_sites_site():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        ANONYMOUS_HEADERS,
        "facility/sites/afb8a6d7-cd5b-4040-8be7-6e917b30af08"
    )


async def check_status_resources():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        ANONYMOUS_HEADERS,
        "status/resources"
    )


async def check_status_resources_resource():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        ANONYMOUS_HEADERS,
        "status/resources/55c1c993-1124-47f9-b823-514ba3849a9a"
    )


async def check_status_incidents():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        ANONYMOUS_HEADERS,
        "status/incidents"
    )


async def check_status_events():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        ANONYMOUS_HEADERS,
        "status/events"
    )


async def check_account_capabilities():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        ANONYMOUS_HEADERS,
        "account/capabilities"
    )


async def check_account_projects():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        HEADERS,
        "account/projects"
    )


async def check_compute_status_polaris():
    return await httpx_post(
        HTTP_TIMEOUT_SEC,
        HEADERS,
        "compute/status/55c1c993-1124-47f9-b823-514ba3849a9a"
    )


async def check_compute_status_crux():
    return await httpx_post(
        HTTP_TIMEOUT_SEC,
        HEADERS,
        "compute/status/8b9b42f7-572a-4909-8472-a0453436304c"
    )


async def check_filesystem_ls():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        HEADERS,
        "filesystem/ls/6115bd2c-957a-4543-abff-5fae52992ff2",
        data={"path": HOME_PATH}
    )


async def check_tasks():
    return await httpx_get(
        HTTP_TIMEOUT_SEC,
        HEADERS,
        "task"
    )
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Post full report including successes")
    args = parser.parse_args()
    asyncio.run(run_checks(full=args.full))