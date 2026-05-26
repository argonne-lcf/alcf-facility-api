from typing import Any
import httpx
from fastapi import HTTPException

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
            raise HTTPException(
                detail=f"Upstream endpoint returned {e.response.status_code}: {e.response.content[:256]!r}.",
                status_code=e.response.status_code,
            )
        elif isinstance(e, httpx.TimeoutException):
            raise HTTPException(
                detail=f"Request timeout.",
                status_code=504,
            )
        elif isinstance(e, httpx.HTTPError):
            raise HTTPException(
                detail=f"HTTP error calling API at {url}: {e}",
                status_code=500
            )
        raise e

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

    async def close(self) -> None:
        await self._client.aclose()
