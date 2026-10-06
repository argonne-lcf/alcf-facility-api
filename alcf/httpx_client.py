from typing import Any
import httpx
from fastapi import HTTPException

from alcf.auth.utils import generate_error_message

class AsyncHttpClient:
    
    def __init__(
        self,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ):
        if headers is None:
            headers = {"Content-Type": "application/json"}
        self.headers = headers
        self._client = httpx.AsyncClient(timeout=timeout, headers=self.headers)

    def _handle_error(self, url: str, e: Exception) -> None:
        if isinstance(e, httpx.HTTPStatusError):
            error_message = generate_error_message(f"Upstream endpoint returned {e.response.status_code}", e)
            raise HTTPException(
                detail=error_message,
                status_code=e.response.status_code,
            )
        if isinstance(e, httpx.TimeoutException):
            raise HTTPException(
                detail=f"Request timeout.",
                status_code=504,
            )
        if isinstance(e, httpx.HTTPError):
            error_message = generate_error_message("HTTP error calling backend API", e)
            raise HTTPException(
                detail=error_message,
                status_code=500
            )

    async def post(self, url: str, data: Any = None) -> Any:
        try:
            response = await self._client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.HTTPError) as e:
            self._handle_error(url, e)

    async def get(self, url: str) -> Any:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.HTTPError) as e:
            self._handle_error(url, e)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        await self._client.aclose()
