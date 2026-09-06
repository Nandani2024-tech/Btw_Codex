# Agent Resurrect (`agent-resurrect-btw`)

## One-sentence summary

An autonomous telemetry circuit breaker and remediation engine that intercepts AI coding agent infinite repair loops, enforces local privacy boundaries, and injects verified team fixes from Databricks Delta Lake.

---

## Problem, intended user and why it matters

Autonomous coding agents (e.g., Claude Code, Codex, Gemini CLI) frequently enter deterministic "doom-loops" when facing architectural, infrastructure, or environmental prerequisites—such as unmocked cluster sockets, missing daemons, or mismatched protocol handshakes.

In these loops:

* Agents perform cosmetic source edits (e.g., altering timeouts, retries, variable names).


* They burn thousands of tokens and API credits within minutes without progressing toward a solution.


* They contaminate local Git histories with failed, unverified rollbacks.



**Target User:** Platform engineers, AI developer teams, and developers supervising autonomous CLI coding agents.

**Why It Matters:** Traditional timeouts kill processes blindly without saving state or identifying root causes. Agent Resurrect actively monitors live execution, trips when consecutive failure thresholds are hit, halts token burn before credit limits exhaust, and surfaces proven cross-repository architectural resolutions.

---

## Selected Entire track and why Entire is essential

* **Selected Track:** **Track 1 – Build a Checkpoint-Native Developer Experience**

* **Why Entire is Essential:**
Git diffs alone only capture what files changed on disk; they cannot capture runtime stderr traces, tool invocation responses, token consumption rates, or why an agent chose a specific remediation path. Entire's Git-ref telemetry flight recorder (`refs/entire/checkpoints/`) captures immutable session events. Agent Resurrect uses this checkpoint stream to calculate failure velocities, detect non-progressing error signatures, and reconstruct sanitized handoff manifests for human or secondary agent resumption.



---

## Architecture and main workflow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Target Sandbox / Client Repo                    │
│                                                                        │
│   Autonomous Agent (Codex / Claude / Gemini)                           │
│        │                                                               │
│        ▼ (Tool executions & test failures)                             │
│   Entire CLI (v0.10.x refspec)                                         │
│        │                                                               │
│        ▼ writes session records to:                                    │
│   refs/entire/checkpoints/<shard>/<ULID>:0/full.jsonl                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    │ Live Polling & Subprocess Supervision
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              Agent Resurrect SDK (agent-resurrect-btw)                 │
│                                                                        │
│   1. resurrect.watcher / cli:                                          │
│      - Subprocess supervisor wrapping agent execution                  │
│      - Live stderr stream analysis & loop detection threshold (N >= 3) │
│      - Process termination & kill escalation (SIGTERM / SIGKILL)       │
│                                                                        │
│   2. resurrect.parser (Track 1 Privacy Boundary):                      │
│      - Regex & AST scrubbing of local file paths (C:\... or /home/...) │
│      - Credential redaction (dapi*, Bearer tokens, private secrets)    │
│      - Extraction of top-level error classes                           │
│                                                                        │
│   3. resurrect.handoff:                                                │
│      - Generates .resurrect/handoff_manifest.json                      │
│      - Computes tokens intercepted & prevented spend ($)               │
│      - Attaches [COMPLETE CONTEXT] vs [PARTIAL CONTEXT] badges         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    │ Parametrized Clean Signature Query
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Databricks Intelligence Store                     │
│                                                                        │
│   Databricks Serverless SQL Warehouse                                  │
│   Delta Lake Table: `dev_failure_traps`                                │
│        │                                                               │
│        ▼ returns:                                                      │
│   - Proven Architectural Fix (e.g. RedisCluster failover)              │
│   - Historical Reference Commit SHA                                    │
│   - Confidence Label ("verified" vs "heuristic")                       │
└────────────────────────────────────────────────────────────────────────┘

```

---

## Entire Graph findings and verification

Before implementing changes to the core CLI and watcher processes, the codebase structure and downstream import implications were evaluated:

* **Graph Definition Lookup:** Mapped dependencies across `resurrect.parser`, `resurrect.core.databricks_client`, `resurrect.handoff`, and `resurrect.watcher`.


* **Impact Analysis:** Identified that altering the `DatabricksClient.fetch_resolution()` signature would directly impact fallback handling across the CLI entry points (`resurrect doctor` and `resurrect run`).


* **Verification Against Source & Tests:** Validated that the privacy boundary sanitization does not truncate core exception classes (`ConnectionError`, `ClusterDownError`), confirmed via 10 automated unit tests passing under `pytest -q`.



---

## Noon Curveball: what changed and how we adapted

* **The Noon Curveball Constraint:** Implementation of a strict **Local Privacy Boundary**. Under no circumstances may raw agent transcripts, local system file paths, or private credentials be transmitted outside the local machine or leaked into cloud Lakehouse queries.


* **How We Adapted:**
1. Preserved stable pre-noon milestone `bc80b6e` and created an Entire Checkpoint.


2. Implemented `sanitize_error_signature()` inside `resurrect.parser` to scrub Windows/POSIX filesystem paths and authentication tokens before payload assembly.
3. Added context-completeness tracking (`ContextStatus`) to tag output metadata explicitly:
* `[COMPLETE CONTEXT]` if full metadata exists without omissions.
* `[PARTIAL / REDACTED CONTEXT]` when prompts or paths are masked.


4. Updated the Databricks query engine to bind only sanitized string signatures to the SQL Statement API parameters, preventing telemetry leakage.




* **Test Proving the Change:** `tests/test_privacy_boundary.py` verifies that paths containing user profiles (`admin`, `nanda`) and API tokens (`dapi*`) are stripped prior to Lakehouse transmission.



---

## Checkpoint links and what each checkpoint proves

| Checkpoint Milestone | Commit / Ref | What It Proves |
| --- | --- | --- |
| **1. Initial Understanding** | `8a7f21b` | Working package skeleton, basic Typer CLI structure (`init`, `doctor`), and Databricks SQL API client integration.

 |
| **2. Pre-Noon Stable State** | `bc80b6e` | Stable Entire Git checkpoint inspection, configuration parser, and initial doctor status reporting table.

 |
| **3. Curveball Adaptation** | `3938b70` | Sanitization engine implemented; local file paths, tokens, and raw prompts isolated behind the Track 1 Privacy Boundary.

 |
| **4. Final Implementation** | `bc78e12` | Live subprocess watcher (`resurrect/watcher.py`), loop breaker thresholding, Databricks Lakehouse fix injection, and PyPI release `0.1.3`.

 |

---

## Setup, run and test instructions

### Prerequisites

* Python 3.11+


* Git 2.40+


* Published SDK: `agent-resurrect-btw` (Available on PyPI)

### 1. Installation

```powershell
pip install --upgrade agent-resurrect-btw

```

### 2. Workspace Initialization & Configuration

In your project repository:

```powershell
resurrect init

```

Populate `.resurrect/config.json` with your Databricks SQL Warehouse credentials (or configure environment variables):

```json
{
  "databricks_host": "https://<your-workspace>.cloud.databricks.com",
  "databricks_token": "dapi...",
  "databricks_warehouse_id": "<your-warehouse-id>",
  "delta_table_name": "dev_failure_traps"
}

```

### 3. Run Pre-Flight Diagnostics

```powershell
resurrect doctor --verbose

```

*Verification:* All checks (`Config`, `Entire`, `Databricks ping`, `Delta table`, `Failure traps`) return green `PASS` badges.

### 4. Running the Circuit Breaker Demo

In your sandbox directory (e.g., `C:\testing_codex`):

```powershell
resurrect run "python simulate_loop.py"

```

*Expected Behavior:*

* The watcher supervises executions across iterations 1 and 2.
* At iteration 3, the circuit breaker trips, sends `SIGTERM`/`SIGKILL` to halt the process, displays the Rich resolution card from Databricks, and creates `.resurrect/handoff_manifest.json`.



### 5. Running the Test Suite

```powershell
pytest -q

```

*Verification:* All unit and privacy tests pass cleanly.

---

## Databricks use, data sources and limitations

### Essential Databricks Capabilities Used

* **Serverless SQL Warehouses (2X-Small):** Executes sub-second, tokenized SQL Statement API calls over HTTPS without requiring a local PySpark or JVM runtime.


* **Delta Lake (`dev_failure_traps`):** Serves as the central repository storing team-wide historical failure traps, architectural resolutions, reference commits, and confidence ratings.



### Delta Lake Seed Schema & Provenance

```sql
CREATE TABLE IF NOT EXISTS dev_failure_traps (
  error_signature STRING,
  module_name STRING,
  resolution STRING,
  commit STRING,
  confidence STRING
) USING DELTA;

MERGE INTO dev_failure_traps AS target
USING (
  SELECT 
    'ConnectionError: Cluster down' AS error_signature,
    'worker.py' AS module_name,
    'Switch to redis.cluster.RedisCluster and configure startup_nodes' AS resolution,
    'commit_8a7f21b' AS commit,
    'verified' AS confidence
) AS source
ON target.error_signature = source.error_signature
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

```

### Data Handling & Offline Fallbacks

* **Responsible Data Handling:** No proprietary customer code or private credentials are stored in Delta Lake or emitted during network transmission.


* **Offline Resilience:** If Databricks Serverless hits warehouse startup latency or network quotas, `DatabricksClient` invokes a local heuristic fallback, ensuring demos and agent handoffs do not crash unhandled.



---

## Known limitations and next steps

* **Token Estimation in Raw Subprocesses:** When running outside an active Entire CLI agent hook, token counts are estimated from captured stdout/stderr buffers rather than raw token metadata.
* **Direct Prompt Injection:** The current release outputs the remediation fix via `.resurrect/handoff_manifest.json` and Rich UI panels; automated reinjection directly into active LLM context windows is planned for v0.2.0.
* **Production Roadmap:**
* Add multi-tenant catalog segregation in Unity Catalog for cross-team failure pattern sharing.
* Integrate native hooks for CI/CD environments (GitHub Actions, GitLab CI) to halt infinite test loops during automated pull request verification.