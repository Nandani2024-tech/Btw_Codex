from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict


class RedisError(Exception):
    pass


class ConnectionError(RedisError):
    pass


class _BaseClient:
    def __init__(self, host: str, port: int, db: int, socket_timeout: int):
        self.host = host
        self.port = port
        self.db = db
        self.socket_timeout = socket_timeout
        self._store: DefaultDict[str, int] = defaultdict(int)

    def ping(self) -> bool:
        return True

    def incr(self, key: str) -> int:
        self._store[key] += 1
        return self._store[key]

    def expire(self, key: str, ttl: int) -> bool:
        return True


class Redis(_BaseClient):
    pass


class RedisCluster(_BaseClient):
    pass


class cluster:
    RedisCluster = RedisCluster


class exceptions:
    RedisError = RedisError
    ConnectionError = ConnectionError
