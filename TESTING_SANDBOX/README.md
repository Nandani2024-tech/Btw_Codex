# E-Commerce Rate Limiter

This microservice models an order-processing pipeline with Redis-backed rate limiting and a separate cluster-health validation step. It also includes a local sanitization boundary for logs so auth tokens, bearer tokens, and IP addresses do not leak past the application boundary. Install dependencies with `pip install -r requirements.txt` and run `pytest` to execute the tests.
