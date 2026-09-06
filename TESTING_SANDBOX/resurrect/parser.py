from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


REQUIRED_CONTEXT_FIELDS = (
    "module",
    "stderr",
    "stdout",
    "tool_output",
    "prompt",
    "message",
    "error",
)
REDACTION_MARKERS = ("[REDACTED]", "***", "<path>", "<token>")
CANONICAL_CLUSTER_ERROR = "redis.exceptions.ClusterDownError"


@dataclass(frozen=True)
class ParsedCheckpoint:
    source_module: str
    error_signature: str
    is_complete: bool
    missing_fields: tuple[str, ...]
    context_label: str
    parser_confidence: str
    lookup_module: str

    @property
    def lookup_mode(self) -> str:
        return "exact" if self.is_complete else "prefix"


def load_checkpoint(path: str | os.PathLike[str] | None = None) -> ParsedCheckpoint:
    """Load exactly one JSON Lines checkpoint from an explicit path or env var."""
    configured_path = path or os.environ.get("RESURRECT_CHECKPOINT_PATH")
    if not configured_path:
        raise ValueError("Set RESURRECT_CHECKPOINT_PATH or pass a checkpoint path.")

    checkpoint_path = Path(configured_path)
    with checkpoint_path.open(encoding="utf-8") as input_file:
        lines = [line for line in input_file if line.strip()]
    if len(lines) != 1:
        raise ValueError("A checkpoint fixture must contain exactly one JSON Lines event.")

    event = json.loads(lines[0])
    if not isinstance(event, dict):
        raise ValueError("Checkpoint event must be a JSON object.")
    return parse_checkpoint_event(event)


def parse_checkpoint_event(event: Mapping[str, Any]) -> ParsedCheckpoint:
    """Create a lookup-safe signature and preserve completeness evidence."""
    missing_fields = tuple(
        field
        for field in REQUIRED_CONTEXT_FIELDS
        if _is_missing_or_redacted(event.get(field))
    )
    error = str(event.get("error", ""))
    signature = _canonical_error_signature(error)
    source_module = str(event.get("module", ""))
    is_complete = not missing_fields

    return ParsedCheckpoint(
        source_module=source_module,
        error_signature=signature,
        is_complete=is_complete,
        missing_fields=missing_fields,
        context_label="complete" if is_complete else "partial",
        parser_confidence="complete" if is_complete else "heuristic",
        # The exception module is query metadata, distinct from the source module.
        lookup_module=signature.rsplit(".", 1)[0].split(".", 1)[0],
    )


def checkpoint_from_exception(exception: Exception, module: str) -> ParsedCheckpoint:
    """Turn a locally caught trap into a lookup-safe, incomplete checkpoint."""
    return parse_checkpoint_event(
        {
            "module": module,
            "error": f"{type(exception).__module__}.{type(exception).__name__}: {exception}",
        }
    )


def _is_missing_or_redacted(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return True
    return any(marker in value for marker in REDACTION_MARKERS)


def _canonical_error_signature(error: str) -> str:
    cluster_match = re.search(
        r"(?:[\w.]*\.)?ClusterDownError:\s*(Redis Cluster node in CLUSTERDOWN state)",
        error,
    )
    if cluster_match:
        return f"{CANONICAL_CLUSTER_ERROR}: {cluster_match.group(1)}"
    return error.strip()
