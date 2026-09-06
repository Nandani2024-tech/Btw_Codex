from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .databricks_client import LookupResult
from .parser import ParsedCheckpoint


def write_handoff_manifest(
    checkpoint: ParsedCheckpoint, lookup: LookupResult, path: str | Path
) -> dict[str, Any]:
    """Write the judge-facing handoff without copying raw checkpoint fields."""
    manifest = {
        "source_module": checkpoint.source_module,
        "error_signature": checkpoint.error_signature,
        "is_complete": checkpoint.is_complete,
        "missing_fields": list(checkpoint.missing_fields),
        "context_label": checkpoint.context_label,
        "query_mode": lookup.query_mode,
        "status_label": lookup.status_label,
        "confidence": lookup.confidence,
        "privacy_boundary": "sanitized-signature-only",
    }
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
