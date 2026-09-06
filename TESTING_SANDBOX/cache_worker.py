"""Rate limiting cache worker backed by Redis."""

from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict

try:
    import redis
except ImportError:  # pragma: no cover - fallback only used when redis is unavailable locally.
    class _RedisError(Exception):
        pass

    class _ConnectionError(_RedisError):
        pass

    class _ClusterRedis:
        pass

    class _RedisClient:
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

    class _RedisNamespace:
        Redis = _RedisClient

        class cluster:
            RedisCluster = _ClusterRedis

        class exceptions:
            RedisError = _RedisError
            ConnectionError = _ConnectionError

    redis = _RedisNamespace()


class RateLimitCacheWorker:
    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0, cluster_mode: bool = False):
        self.host = host
        self.port = port
        self.db = db
        self.cluster_mode = cluster_mode
        self.client = redis.Redis(host=host, port=port, db=db, socket_timeout=2)

    def is_cluster_healthy(self) -> bool:
        if not self.cluster_mode:
            return True

        if not isinstance(self.client, redis.cluster.RedisCluster):
            raise redis.exceptions.ConnectionError(
                "Redis Cluster node in CLUSTERDOWN state. Handshake rejected: standalone client used on cluster topology."
            )

        return True

    def check_rate_limit(self, user_id: str, max_requests: int = 100) -> bool:
        key = f"rate:{user_id}"
        count = self.client.incr(key)

        if count == 1:
            try:
                self.client.expire(key, 60)
            except redis.exceptions.RedisError:
                pass

        return count <= max_requests
