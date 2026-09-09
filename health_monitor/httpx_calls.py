import httpx
import logging
import os

from dotenv import load_dotenv

from logging_config import configure_logging

configure_logging()
log = logging.getLogger(__name__)


load_dotenv(override=True)


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/api/v1")
if BASE_URL.endswith("/"):
    BASE_URL = BASE_URL[:-1]


def _format_error(relative_url: str, e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        return f"{relative_url}: {e!r}\nResponse body: {e.response.text}"
    return f"{relative_url}: {e!r}"


async def httpx_get(timeout, headers, relative_url, data=None) -> tuple[bool, str]:
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        try:
            response = await client.get(f"{BASE_URL}/{relative_url}", params=data)
            response.raise_for_status()
            return True, f"{relative_url}: ok"
        except Exception as e:
            message = _format_error(relative_url, e)
            log.error(message)
            return False, message


async def httpx_post(timeout, headers, relative_url) -> tuple[bool, str]:
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        try:
            response = await client.post(f"{BASE_URL}/{relative_url}")
            response.raise_for_status()
            return True, f"{relative_url}: ok"
        except Exception as e:
            message = _format_error(relative_url, e)
            log.error(message)
            return False, message