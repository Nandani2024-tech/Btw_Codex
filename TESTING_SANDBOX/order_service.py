from cache_worker import RateLimitCacheWorker


class OrderProcessor:
    def __init__(self, cache_worker: RateLimitCacheWorker):
        self.cache_worker = cache_worker

    def process_order(self, order_id: str, user_id: str, amount: float) -> dict:
        # Check cluster health first
        self.cache_worker.is_cluster_healthy()

        # Check rate limiting
        if not self.cache_worker.check_rate_limit(user_id):
            return {"status": "RATE_LIMITED", "order_id": order_id}

        return {"status": "CONFIRMED", "order_id": order_id, "amount": amount}
