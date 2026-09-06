from __future__ import annotations
from collections import defaultdict
from typing import DefaultDict
import redis


class RateLimitCacheWorker:
    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0, cluster_mode: bool = False):
        self.host = host
        self.port = port
        self.db = db
        self.cluster_mode = cluster_mode
        self.client = redis.Redis(host=host, port=port, db=db, socket_timeout=1)
        self._memory_store: DefaultDict[str, int] = defaultdict(int)

    def is_cluster_healthy(self) -> bool:
        if self.cluster_mode and not isinstance(self.client, getattr(redis.cluster, "RedisCluster", type(None))):
            raise redis.exceptions.ConnectionError(
                "Redis Cluster node in CLUSTERDOWN state. Handshake rejected: standalone client used on cluster topology."
            )
        return True

    def check_rate_limit(self, user_id: str, max_requests: int = 100) -> bool:
        key = f"rate:{user_id}"
        self._memory_store[key] += 1
        return self._memory_store[key] <= max_requests
