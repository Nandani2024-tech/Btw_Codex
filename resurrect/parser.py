"""Telemetry parsing and privacy sanitization for checkpoint context."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
from typing import Any


REDACTION_MARKERS = ("[REDACTED]", "***")
DEFAULT_CHECKPOINT_DIR = Path("refs/entire/checkpoints")


@dataclass(slots=True)
class ContextStatus:
    is_complete: bool
    confidence: str
    missing_fields: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ParsedTelemetry:
    error_signature: str = ""
    module_names: list[str] = field(default_factory=list)
    privacy_provenance: str = "sanitized"
    status: ContextStatus = field(default_factory=lambda: ContextStatus(is_complete=False, confidence="partial"))
    source_path: Path | None = None


def _looks_redacted(text: str) -> bool:
    return any(marker in text for marker in REDACTION_MARKERS)


def sanitize_error_signature(raw_trace: str) -> str:
    if not raw_trace:
        return ""

    text = re.sub(r"(?i)\b[A-Z]:\\[^\s\n\r\t]+", "<path>", raw_trace)
    text = re.sub(r"(?i)(?:/[^ \n\r\t]+)+", "<path>", text)
    text = re.sub(r"\bdapi[a-zA-Z0-9]+\b", "<token>", text)
    text = re.sub(r"(?i)Bearer\s+[a-zA-Z0-9._-]+", "Bearer <token>", text)

    match = re.search(r"([A-Z]\w*(?:Error|Exception)[^\n]*)", text)
    if match:
        return match.group(1).strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _sanitize_text(text: str) -> str:
    text = re.sub(r"(?i)\b(token|password|secret|api[_-]?key)\s*[:=]\s*[^ \n\r\t]+", r"\1=<redacted>", text)
    text = re.sub(r"(?i)\b[0-9a-f]{16,}\b", "<token>", text)
    text = re.sub(r"`[^`]+`", "<redacted>", text)
    return sanitize_error_signature(text).strip()


def _extract_exception_signature(text: str) -> str:
    if not text:
        return "UnknownError: missing checkpoint content"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "UnknownError: empty checkpoint content"
    for line in reversed(lines):
        if ":" in line:
            return _sanitize_text(line)
    return _sanitize_text(lines[-1])


def _extract_module_names(events: list[dict[str, Any]]) -> list[str]:
    modules: set[str] = set()
    for event in events:
        module = event.get("module") or event.get("tool") or event.get("source")
        if isinstance(module, str) and module:
            modules.add(module.split(".")[0])
    return sorted(modules)


def _read_checkpoint_records(checkpoint_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    missing_fields: list[str] = []
    if not checkpoint_dir.exists():
        missing_fields.append("checkpoint_dir")
        return records, missing_fields
    for path in sorted(checkpoint_dir.glob("**/*.jsonl")):
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    missing_fields.append(f"truncated_line:{path.name}")
                    continue
                if isinstance(record, dict):
                    records.append(record)
        except OSError:
            missing_fields.append(f"unreadable:{path.name}")
    return records, missing_fields


def parse_telemetry(checkpoint_dir: Path | None = None, fixture_path: Path | None = None) -> ParsedTelemetry:
    checkpoint_root = checkpoint_dir or DEFAULT_CHECKPOINT_DIR
    records, missing_fields = _read_checkpoint_records(checkpoint_root)
    source_path: Path | None = checkpoint_root if records else None

    if not records and fixture_path and fixture_path.exists():
        source_path = fixture_path
        try:
            for line in fixture_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip():
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        records.append(obj)
        except (OSError, json.JSONDecodeError):
            missing_fields.append("fixture_parse_failed")

    transcript_parts: list[str] = []
    redacted = False
    for record in records:
        if "prompt" not in record:
            missing_fields.append("prompt")
        if "stderr" not in record and "stdout" not in record:
            missing_fields.append("tool_output")
        for field in ("prompt", "transcript", "stderr", "stdout", "error", "message"):
            value = record.get(field)
            if isinstance(value, str) and value:
                if _looks_redacted(value):
                    redacted = True
                transcript_parts.append(value)
    transcript = "\n".join(transcript_parts)
    if _looks_redacted(transcript):
        redacted = True
    signature = _extract_exception_signature(transcript)
    status = ContextStatus(
        is_complete=not redacted and not missing_fields,
        confidence="complete" if not redacted and not missing_fields else "partial",
        missing_fields=sorted(set(missing_fields)),
    )
    return ParsedTelemetry(
        error_signature=signature,
        module_names=_extract_module_names(records),
        privacy_provenance="checkpoint" if source_path == checkpoint_root else "fixture",
        status=status,
        source_path=source_path,
    )
