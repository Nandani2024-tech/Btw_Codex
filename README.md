# Agent Resurrect (`agent-resurrect-btw`)

[![PyPI](https://img.shields.io/pypi/v/agent-resurrect-btw.svg)](https://pypi.org/project/agent-resurrect-btw/)
[![Track](https://img.shields.io/badge/BTW%202026-Track%201%20Privacy%20Boundary-blue.svg)](https://bengaluru-tech-week.com)

**Agent Resurrect** is an autonomous telemetry and circuit-breaking engine for AI coding agents (Claude Code, Codex, Gemini CLI). It prevents infinite repair "doom-loops", safeguards API budgets, and retrieves team-wide resolutions stored in Databricks Delta Lake.

---

## Quick Start

### 1. Installation
Install the SDK from PyPI:

```bash
pip install --upgrade agent-resurrect-btw
```

### 2. Initialize in Your Repository
Run in your project root:

```bash
resurrect init
```

This enables Entire checkpoint tracking and creates a starter configuration file at:

```text
.resurrect/config.json
```

### 3. Configure Databricks Credentials
Open `.resurrect/config.json` and fill in your connection details:

```json
{
  "databricks_host": "https://<your-workspace>.cloud.databricks.com",
  "databricks_token": "dapi...",
  "databricks_warehouse_id": "<your-warehouse-id>",
  "delta_table_name": "dev_failure_traps"
}
```

### Alternative: Environment Variables
You can also supply credentials via your environment without editing files:

```bash
export DATABRICKS_HOST="https://<your-workspace>.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi..."
export DATABRICKS_WAREHOUSE_ID="<your-warehouse-id>"
export DELTA_TABLE_NAME="dev_failure_traps"
```

### 4. Run Pre-Flight Diagnostics
Validate connectivity to Git, Entire CLI, and Databricks SQL Serverless:

```bash
resurrect doctor
```

For deep-dive logs and command traces, append `--verbose`:

```bash
resurrect doctor --verbose
```

## Usage

### Live Agent Execution & Circuit Breaking
Execute your coding agent or test suite wrapped in the Resurrect telemetry harness:

```bash
resurrect run "pytest test_redis_worker.py"
```

Or with an interactive agent:

```bash
resurrect run "codex 'fix the failing cluster connection in worker.py'"
```

How It Works:

- Live Subprocess Supervision: Resurrect streams agent output live in the terminal.
- Loop Detection: Evaluates consecutive failure signatures from Entire Git checkpoints (`refs/entire/checkpoints/`).
- Emergency Circuit Breaker: When failure counts reach 3, execution halts immediately to prevent token and credit burn.
- Lakehouse Remediation: Fetches proven fixes from Databricks Delta Lake (`dev_failure_traps`).
- Handoff Manifest: Generates `.resurrect/handoff_manifest.json` with token counts, cost saved estimates, and context badges.

### Inspect Checkpoints & Telemetry
Inspect the latest session checkpoint, token estimates, and privacy status:

```bash
resurrect inspect-checkpoint
```

## Track 1: Privacy Boundary Compliance

Agent Resurrect includes a local security and sanitization boundary:

- Zero Leakage: Raw prompts, full stack frames, and transcripts are never sent to external services.
- Token & Path Scrubbing: Local paths (`C:\Users\...`) and secrets (`dapi...`, `Bearer...`) are scrubbed before SQL query generation.
- Explicit Context Transparency: Output is badged as `[COMPLETE CONTEXT]` or `[PARTIAL / REDACTED CONTEXT]` so downstream engineers know whether fixes are verified or heuristic.
