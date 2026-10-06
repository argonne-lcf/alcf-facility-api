import redis
import logging
from alcf.config import REDIS_HOST, REDIS_PORT

log = logging.getLogger(__name__)

# Redis client for caching
_redis_client = None

def get_redis_client():
    """Get or create Redis client connection"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True
            )
            _redis_client.ping()  # Test connection
        except Exception as e:
            log.warning(f"Failed to connect to Redis: {e}")
            _redis_client = None
    return _redis_client
