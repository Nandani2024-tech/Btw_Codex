import pytest
from cache_worker import RateLimitCacheWorker
from order_service import OrderProcessor


def test_order_rate_limiting():
    worker = RateLimitCacheWorker()
    for _ in range(100):
        assert worker.check_rate_limit("test_user", max_requests=100) is True
    assert worker.check_rate_limit("test_user", max_requests=100) is False


def test_order_processing_success():
    worker = RateLimitCacheWorker(cluster_mode=False)
    processor = OrderProcessor(cache_worker=worker)
    result = processor.process_order("ORD-001", "test_user", 99.99)
    assert result["status"] == "CONFIRMED"


def test_enterprise_cluster_checkout():
    worker = RateLimitCacheWorker(cluster_mode=True)
    processor = OrderProcessor(cache_worker=worker)
    with pytest.raises(Exception, match="Redis Cluster node in CLUSTERDOWN state"):
        processor.process_order("ORD-1001", "USR-99", 250.00)

