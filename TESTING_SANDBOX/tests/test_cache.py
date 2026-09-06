import pytest
from cache_worker import RateLimitCacheWorker

def test_standalone_worker_init():
    worker = RateLimitCacheWorker(cluster_mode=False)
    assert worker.is_cluster_healthy() is True

def test_rate_limit_counter():
    worker = RateLimitCacheWorker()
    assert worker.check_rate_limit("user_123") is True

def test_cluster_topology_connection():
    worker = RateLimitCacheWorker(cluster_mode=True)
    # This must call is_cluster_healthy() to trigger the cluster mismatch error
    assert worker.is_cluster_healthy() is True
