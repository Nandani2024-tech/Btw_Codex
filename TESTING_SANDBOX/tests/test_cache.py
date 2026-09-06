import cache_worker
import pytest

import cache_worker
from cache_worker import RateLimitCacheWorker
from unittest.mock import MagicMock

def test_standalone_worker_init():
    worker = RateLimitCacheWorker(cluster_mode=False)
    assert worker.is_cluster_healthy() is True

def test_rate_limit_counter():
    worker = RateLimitCacheWorker()
    worker.client = MagicMock()
    worker.client.incr.side_effect = [1]
    worker.client.expire.return_value = True
    assert worker.check_rate_limit("user_123") is True

def test_cluster_topology_connection():
    worker = RateLimitCacheWorker(cluster_mode=True)
    with pytest.raises(
        cache_worker.redis.exceptions.ClusterDownError,
        match="Redis Cluster node in CLUSTERDOWN state",
    ):
        worker.is_cluster_healthy()
