# Phase 10D — Governance Analytics

Engineering reference for the governance analytics layer added in Phase 10D.

---

## What was built

The governance analytics layer collects runtime signals from the presentation
pipeline and persists them for offline analysis.  It is entirely additive:
no pipeline behaviour changes depending on analytics availability, and all
writes are non-blocking (failures are logged, never raised).

Four capabilities were added:

| Sub-phase | Capability |
|-----------|-----------|
| 10D.1 | Data models (`FailureAttribution`, `ArtifactUsageEvent`, `GovernanceAuditEvent`, `RunRecord`) |
| 10D.2 | `PipelineResult.run_id` — UUID4 generated per call |
| 10D.3 | Usage event capture and `RunRecord` emission |
| 10D.4 | Analytics writer (`run_records.jsonl`, `usage_events.jsonl`, `usage_aggregates.json`) |
| 10D.5 | Telemetry hardening, failure attribution, per-run usage snapshots, daily aggregates |

---

## Persisted artifacts

All paths are relative to `analytics_dir` (configured via
`PPTGEN_ANALYTICS_DIR`; empty string = analytics disabled).

```
governance/
  usage_runs/
    <run_id>/
      artifact_usage_snapshot.json   # per-run usage records (source of truth)
      failure_attribution.json       # present only on failed runs
  aggregates/
    daily/
      <YYYY-MM-DD>/
        artifact_version_usage.json  # rebuilt after every run on that day
    latest/
      artifact_version_usage_latest.json  # copy of the most-recently updated day
```

### `artifact_usage_snapshot.json`

A JSON array of serialised `ArtifactUsageRecord` objects — one entry per
distinct `(artifact_type, artifact_family, artifact_version, usage_scope)`
observed in the run.  Records are written only on success **and** failure
paths (see failure path below).

Key fields:

| Field | Meaning |
|-------|---------|
| `run_id` | UUID4 identifying the pipeline call |
| `run_ts` | ISO 8601 UTC timestamp of run start |
| `artifact_type` | `"primitive"`, `"layout"`, `"theme"`, `"token_set"`, `"asset"` |
| `artifact_family` | Stable artifact identifier (slug) |
| `artifact_version` | Resolved version string, or `null` for ungoverned |
| `lifecycle_state` | `"approved"`, `"deprecated"`, `"draft"` |
| `usage_scope` | `"top_level"`, `"dependency"`, `"per_slide"` |
| `resolution_source` | `"explicit"` (named in YAML) or `"default"` (from settings) |
| `warning_emitted` | `true` if a deprecation warning was surfaced |
| `is_draft_override_usage` | `true` if a DRAFT artifact was used via override |
| `used_in_successful_run` | `true` when `finalize_usage(True)` called |
| `used_in_failed_run` | `true` when `finalize_usage(False)` called |

### `failure_attribution.json`

Written only when the pipeline raises `PipelineError`.  Contains a single
`RunFailureAttribution` object identifying the stage, candidate artifact, and
attribution confidence (`"high"` for governance/resolution errors, `"medium"`
for render/export, `"low"` for unknown).

### `artifact_version_usage.json` (daily aggregate)

A JSON array of `ArtifactVersionUsageAggregate` objects sorted by
`(artifact_type, artifact_family, artifact_version)`.  Rebuilt from scratch
each time any run on that day completes.

---

## Aggregate semantics

All aggregate counts are **per distinct `run_id`**, not per record.
A single run may produce multiple `ArtifactUsageRecord` entries for the same
artifact (e.g. the same primitive used at `top_level` and `per_slide`), but
that run contributes at most 1 to every count.

| Field | Rule |
|-------|------|
| `run_count` | Number of distinct `run_id` values for this (type, family, version) key |
| `success_count` | Runs where any record had `used_in_successful_run=True` |
| `failure_count` | Runs where any record had `used_in_failed_run=True` |
| `explicit_usage_count` | Runs where any record had `resolution_source="explicit"` |
| `default_usage_count` | `run_count - explicit_usage_count` (mutually exclusive) |
| `draft_override_count` | Runs where any record had `is_draft_override_usage=True` |
| `deprecated_warning_count` | Runs where any record had `warning_emitted=True` |

**Invariants** (always hold; enforced by construction):

- `explicit_usage_count + default_usage_count == run_count`
- `explicit_usage_count <= run_count`
- `default_usage_count <= run_count`
- `draft_override_count <= run_count`
- `deprecated_warning_count <= run_count`
- `success_count + failure_count <= run_count` (a run can be both if two except
  blocks fire — rare but possible with OSError on export after a successful render)

Within-run signal merge rules (applied when multiple records share the same
`run_id` for the same aggregate key):

- `warning_emitted` → OR
- `is_draft_override_usage` → OR
- `resolution_source` → `"explicit"` overrides `"default"`; first-wins for all
  other values

---

## Rebuild model

Aggregates are **derived exclusively from persisted snapshot files**.
In-memory pipeline state is never used by the summariser.

To rebuild aggregates after data loss or schema changes:

```python
from pathlib import Path
from pptgen.analytics import rebuild_all_aggregates

rebuild_all_aggregates(Path("/path/to/analytics_dir"))
```

This replays all `artifact_usage_snapshot.json` files in
`governance/usage_runs/`, groups records by `run_ts` date, and rewrites
every daily aggregate file plus the `latest` file.

To rebuild a single day:

```python
from datetime import date
from pptgen.analytics import update_daily_aggregates

update_daily_aggregates(Path("/path/to/analytics_dir"), date(2026, 3, 28))
```

---

## What is intentionally excluded

- **Persistent dependency graph** — dependency capture (`dependency_chain` on
  `PipelineResult`) is runtime-local and not persisted.
- **Brand artifact governance** — brands have no governance blocks; the pattern
  for adding them later is documented in the Phase 10 memory notes.
- **Per-slide primitive capture** — per-slide primitives go through
  `_normalize_primitive_slides` at render time; only the top-level `primitive:`
  key is captured in the dependency chain.
- **Dashboards / query APIs** — the analytics layer writes flat JSON files only.
  Querying and visualisation are out of scope.
- **Cross-day aggregation** — each daily file is independent; weekly/monthly
  roll-ups are not implemented.
- **Aggregate dimensions beyond (type, family, version)** — usage scope,
  resolution source, and other dimensions are available as raw signals in the
  snapshot but are not broken out in the aggregate schema.

---

## Key source locations

| File | Purpose |
|------|---------|
| `src/pptgen/analytics/analytics_models.py` | Core data models |
| `src/pptgen/analytics/aggregate_models.py` | `ArtifactVersionUsageAggregate` |
| `src/pptgen/analytics/aggregate_summarizer.py` | `build_daily_aggregates`, `update_daily_aggregates`, `rebuild_all_aggregates` |
| `src/pptgen/analytics/telemetry.py` | `GovernanceTelemetryCollector` |
| `src/pptgen/analytics/writer.py` | All non-blocking file writers |
| `src/pptgen/pipeline/generation_pipeline.py` | Wiring: telemetry capture, failure attribution, write calls |
