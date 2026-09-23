import hashlib
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from alcf.cache.redis import get_redis_client
from alcf.config import RATE_LIMIT_ENABLED, RATE_LIMIT_GLOBAL_RATE, RATE_LIMIT_USER_RATE

log = logging.getLogger(__name__)

GLOBAL_KEY = "rate_limit:global"
USER_KEY_PREFIX = "rate_limit:user:"

# Atomically increment a fixed-window counter and set TTL on first hit.
# Returns the current count after increment.
_LUA_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], 1)
end
return count
"""


def _extract_token_hash(request: Request) -> str | None:
    """Hash the bearer token to use as a stable per-user rate limit key."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.removeprefix("Bearer ")
    return hashlib.sha256(token.encode()).hexdigest()


def _is_limited(redis_client, key: str, limit: int) -> bool:
    """Return True if the request exceeds the rate limit for the given key."""
    try:
        count = redis_client.eval(_LUA_SCRIPT, 1, key)
        return count > limit
    except Exception as e:
        log.warning(f"Rate limit check failed: {e}")
        return False  # Fail open: let the request through if Redis is unavailable


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not RATE_LIMIT_ENABLED:
            return await call_next(request)

        redis_client = get_redis_client()
        if redis_client is None:
            log.warning("Redis unavailable, skipping rate limiting")
            return await call_next(request)

        if _is_limited(redis_client, GLOBAL_KEY, RATE_LIMIT_GLOBAL_RATE):
            return JSONResponse(
                status_code=429, 
                content={
                    "status": 429,
                    "title": "Too Many Requests",
                    "detail": f"Global rate limit of {RATE_LIMIT_GLOBAL_RATE} reqs/sec exceeded."
                },
                headers={"Retry-After": "1"}
            )

        token_hash = _extract_token_hash(request)
        if token_hash and _is_limited(redis_client, f"{USER_KEY_PREFIX}{token_hash}", RATE_LIMIT_USER_RATE):
            return JSONResponse(
                status_code=429, 
                content={
                    "status": 429,
                    "title": "Too Many Requests",
                    "detail": f"Per-user rate limit of {RATE_LIMIT_USER_RATE} reqs/sec exceeded."
                },
                headers={"Retry-After": "1"}
            )

        return await call_next(request)
