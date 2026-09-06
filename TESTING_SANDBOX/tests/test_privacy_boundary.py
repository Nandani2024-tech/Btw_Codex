from __future__ import annotations

import json
from pathlib import Path

import pytest

from cache_worker import RateLimitCacheWorker
from order_service import OrderProcessor
from resurrect.databricks_client import DatabricksClient
from resurrect.parser import checkpoint_from_exception, load_checkpoint


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_full_checkpoint_is_complete_context() -> None:
    checkpoint = load_checkpoint(FIXTURES / "full_checkpoint.jsonl")

    assert checkpoint.is_complete is True
    assert checkpoint.missing_fields == ()
    assert checkpoint.context_label == "complete"
    assert checkpoint.parser_confidence == "complete"


def test_redacted_checkpoint_is_partial_and_never_verified() -> None:
    checkpoint = load_checkpoint(FIXTURES / "redacted_checkpoint.jsonl")
    result = DatabricksClient().build_statement_payload(checkpoint)

    assert checkpoint.is_complete is False
    assert checkpoint.missing_fields == ("stderr", "stdout", "tool_output", "prompt", "message")
    assert checkpoint.context_label == "partial"
    assert checkpoint.parser_confidence == "heuristic"
    assert "=" not in result["statement"].split("WHERE", 1)[1].split("AND", 1)[0]


def test_redacted_payload_contains_only_safe_lookup_metadata() -> None:
    checkpoint = load_checkpoint(FIXTURES / "redacted_checkpoint.jsonl")
    payload = DatabricksClient(warehouse_id="warehouse-test").build_statement_payload(checkpoint)
    payload_text = json.dumps(payload)

    assert ":error_signature" in payload["statement"]
    assert ":module_0" in payload["statement"]
    for forbidden in (
        "D:\\\\BTW_CODEX",
        "orders.internal.example",
        "10.24.8.19",
        "dapi_demo_full_token_123456",
        "demo-api-key-123",
        "Investigate the checkout failure",
        "stderr",
        "prompt",
    ):
        assert forbidden not in payload_text


def test_cluster_trap_produces_cluster_down_signature_end_to_end() -> None:
    worker = RateLimitCacheWorker(cluster_mode=True)
    processor = OrderProcessor(cache_worker=worker)

    with pytest.raises(Exception) as captured:
        processor.process_order("ORD-1001", "USR-99", 250.00)

    checkpoint = checkpoint_from_exception(captured.value, module="cache_worker")
    assert checkpoint.error_signature == (
        "redis.exceptions.ClusterDownError: Redis Cluster node in CLUSTERDOWN state"
    )
