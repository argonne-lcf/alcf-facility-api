import logging
import time
from abc import ABC, abstractmethod
from typing import Optional
from threading import RLock

from alcf.cache.redis import get_redis_client

log = logging.getLogger(__name__)


class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        pass
    @abstractmethod
    def set(self, key: str, value: str, ttl: int = 60):
        pass


class RedisCache(CacheBackend):
    """Redis cache for serializable function results."""

    def __init__(self):
        self.redis = get_redis_client()

    def get(self, key: str) -> Optional[str]:
        try:
            return self.redis.get(key)
        except Exception as e:
            return None

    def set(self, key: str, value: str, ttl: int = 60):
        try:
            self.redis.set(key, value, ex=ttl)
        except Exception as e:
            log.warning(f"Could not cache with Redis. Key: {key}. Execption: {e}")
            pass


class MemoryCache(CacheBackend):
    """Memory cache for non-serializable function results."""

    def __init__(self, maxsize: int = 1024):
        self.cache = {}
        self.maxsize = maxsize
        self.lock = RLock()

    def get(self, key: str) -> Optional[str]:
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    return value
                else:
                    del self.cache[key]
            return None

    def set(self, key: str, value: str, ttl: int = 60):
        with self.lock:
            if key in self.cache: # Remove existing key so we re-insert as newest
                del self.cache[key]
            elif len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False) # Remove last entry if cache already full
            self.cache[key] = (value, time.time() + ttl)