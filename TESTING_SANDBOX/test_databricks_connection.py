from __future__ import annotations

import json
import os
import sys
from urllib import error, request


def main() -> int:
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")

    missing = [
        name
        for name, value in (
            ("DATABRICKS_HOST", host),
            ("DATABRICKS_TOKEN", token),
            ("DATABRICKS_WAREHOUSE_ID", warehouse_id),
        )
        if not value
    ]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    base_url = host.rstrip("/")
    url = f"{base_url}/api/2.0/sql/statements"
    payload = {
        "warehouse_id": warehouse_id,
        "statement": "SELECT * FROM dev_failure_traps WHERE error_signature LIKE '%ClusterDownError%'",
        "wait_timeout": "10s",
        "format": "JSON_ARRAY",
    }

    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"HTTP {resp.status}")
            print(body)
            return 0
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}")
        print(body)
        return exc.code or 1
    except error.URLError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
