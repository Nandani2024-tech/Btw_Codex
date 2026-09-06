"""Handoff manifest assembly for privacy-aware checkpoint resolution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from resurrect.parser import ParsedTelemetry


@dataclass(slots=True)
class HandoffManifest:
    status_label: str
    resolution_kind: str
    privacy_provenance: str
    confidence: str
    error_signature: str
    module_names: list[str] = field(default_factory=list)
    is_complete: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def build_handoff_manifest(telemetry: ParsedTelemetry, verified_match: bool) -> HandoffManifest:
    partial = not telemetry.status.is_complete or telemetry.status.confidence != "complete" or not verified_match
    return HandoffManifest(
        status_label="[PARTIAL / REDACTED CONTEXT]" if partial else "[COMPLETE CONTEXT]",
        resolution_kind="heuristic" if partial else "verified",
        privacy_provenance=telemetry.privacy_provenance,
        confidence=telemetry.status.confidence,
        error_signature=telemetry.error_signature,
        module_names=telemetry.module_names,
        is_complete=telemetry.status.is_complete and verified_match,
        metadata={
            "missing_fields": telemetry.status.missing_fields,
            "source_path": str(telemetry.source_path) if telemetry.source_path else None,
        },
    )


def write_handoff_manifest(path: Path, telemetry: ParsedTelemetry, verified_match: bool) -> Path:
    path.write_text(build_handoff_manifest(telemetry, verified_match).to_json(), encoding="utf-8")
    return path


def generate_handoff_manifest(session_data: dict, remediation: dict, filepath: str = "handoff_manifest.json") -> str:
    payload = {
        "session_data": session_data,
        "remediation": remediation,
    }
    path = Path(filepath)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)
