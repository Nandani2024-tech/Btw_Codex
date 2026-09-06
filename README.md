# Agent Resurrect SDK

Agent Resurrect is a real-time loop-breaker and telemetry co-pilot for agentic workflows. It is designed to sit alongside a Databricks-backed failure trap table, observe agent activity, and provide the control surface needed to inspect, diagnose, and recover from runaway loops.

This repository currently contains the foundational SDK scaffold only. The business logic, Databricks integration, and runtime loop-breaking behavior will be added incrementally on top of this structure.

## Project Layout

```text
resurrect/
  __init__.py
  cli.py
  config.py
  core/
    __init__.py
    entire_bridge.py
    databricks_client.py
  ui/
    __init__.py
    console.py
tests/
  __init__.py
  test_config.py
  test_connectivity.py
```

## Planned CLI

The `resurrect` command will eventually expose these entry points:

- `resurrect init`
- `resurrect doctor`
- `resurrect run`

Those commands are not implemented yet. The current CLI module only provides a minimal Typer application stub so the package can be installed and extended safely.

## Environment Variables

Copy `.env.example` to `.env` and populate the Databricks connection settings:

- `DATABRICKS_HOST`
- `DATABRICKS_TOKEN`
- `DATABRICKS_WAREHOUSE_ID`
- `DELTA_TABLE_NAME`

## Build Metadata

- Package name: `agent-resurrect`
- Version: `0.1.0`
- Entry point: `resurrect`

