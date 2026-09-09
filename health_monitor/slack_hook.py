import httpx
import logging
import os
from dotenv import load_dotenv

load_dotenv(override=True)

log = logging.getLogger(__name__)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")


async def post_to_slack(message: str) -> None:
    if not WEBHOOK_URL:
        log.warning("WEBHOOK_URL not set; skipping Slack notification")
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            _ = await client.post(WEBHOOK_URL, json={"text": message})
    except httpx.HTTPStatusError as e:
        log.error(
            "Failed to post to Slack: HTTP %s %s",
            e.response.status_code,
            e.response.text,
        )
    except Exception as e:
        log.error("Error posting to Slack: %s", e)