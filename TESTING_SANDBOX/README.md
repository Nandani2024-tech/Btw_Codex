# Cache Rate Limiter

This microservice provides a small Redis-backed rate-limiting worker that can be used to guard request-heavy endpoints. It includes a standalone client path plus a cluster-mode health check to reflect common production deployment patterns. Install dependencies with `pip install -r requirements.txt` and run `pytest` to execute the tests.