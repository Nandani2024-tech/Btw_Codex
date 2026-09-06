from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .databricks_client import DatabricksClient
from .handoff import write_handoff_manifest
from .parser import load_checkpoint


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the privacy-safe resurrect pipeline.")
    parser.add_argument("--checkpoint", help="JSONL checkpoint; overrides RESURRECT_CHECKPOINT_PATH.")
    parser.add_argument(
        "--handoff-path",
        default=os.environ.get("RESURRECT_HANDOFF_PATH", "handoff_manifest.json"),
        help="Output path for the sanitized handoff manifest.",
    )
    args = parser.parse_args()

    checkpoint = load_checkpoint(args.checkpoint)
    lookup = DatabricksClient().lookup(checkpoint)
    manifest = write_handoff_manifest(checkpoint, lookup, Path(args.handoff_path))
    print(
        json.dumps(
            {
                "parsed_error_signature": checkpoint.error_signature,
                "is_complete": checkpoint.is_complete,
                "parser_confidence": checkpoint.parser_confidence,
                "query_mode": lookup.query_mode,
                "status_label": lookup.status_label,
                "confidence": lookup.confidence,
                "statement_payload": lookup.statement_payload,
                "databricks_response": lookup.response,
                "handoff_manifest": manifest,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
