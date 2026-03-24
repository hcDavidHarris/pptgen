# Artifact and Run Management

Stage 6C adds durable run tracking, artifact registration, filesystem promotion, manifest
generation, and retention policy enforcement.

---

## Architecture Overview

```
Job (Stage 6B)
 └── RunRecord (Stage 6C)
      ├── ArtifactRecord: pptx
      ├── ArtifactRecord: spec
      ├── ArtifactRecord: slide_plan
      ├── ArtifactRecord: deck_definition
      └── ArtifactRecord: manifest
```

### Storage Layers

**Ephemeral workspace** (unchanged):
```
$PPTGEN_WORKSPACE_BASE/<run_id>/
  output.pptx
  artifacts/
    spec.json
    slide_plan.json
    deck_definition.json
```

**Durable artifact store** (new):
```
$PPTGEN_ARTIFACT_STORE_BASE/
  runs/
    <run_id>/
      output.pptx           ← promoted copy
      spec.json
      slide_plan.json
      deck_definition.json
      manifest.json         ← written last
```

---

## Entity Model

### RunRecord

Represents a single generation pipeline execution.

| Field | Type | Description |
|---|---|---|
| `run_id` | str | 32-hex unique identifier (shared with workspace) |
| `status` | `RunStatus` | `running` → `succeeded` / `failed` / `cancelled` |
| `source` | `RunSource` | `api_sync`, `api_async`, `cli`, `batch` |
| `job_id` | str | Linked `JobRecord.job_id` for async runs |
| `playbook_id` | str | Playbook chosen by input router |
| `template_id` | str | Template used |
| `manifest_path` | str | Relative path to `manifest.json` in artifact store |

### ArtifactRecord

Represents a single promoted file.

| Field | Type | Description |
|---|---|---|
| `artifact_id` | str | 32-hex unique identifier |
| `run_id` | str | Parent run |
| `artifact_type` | `ArtifactType` | `pptx`, `spec`, `slide_plan`, `deck_definition`, `manifest`, `log`, `diagnostic` |
| `relative_path` | str | Path relative to `artifact_store_base` |
| `checksum` | str | `sha256:<hex>` |
| `visibility` | `ArtifactVisibility` | `downloadable` (pptx only) or `internal` |
| `retention_class` | `ArtifactRetentionClass` | `always`, `longest`, `medium`, `shorter` |

### Artifact Policy Matrix

| Type | Visibility | Retention | Final Output |
|---|---|---|---|
| `pptx` | downloadable | longest (7d) | yes |
| `manifest` | internal | always | no |
| `spec` | internal | medium (3d) | no |
| `slide_plan` | internal | medium (3d) | no |
| `deck_definition` | internal | medium (3d) | no |
| `log` | internal | shorter (1d) | no |
| `diagnostic` | internal | shorter (1d) | no |

---

## Promotion Flow

After `generate_presentation()` completes:

```
ArtifactPromoter.promote(run, workspace_root, artifacts_subdir)
  ├── copy output.pptx → artifact_store/runs/<run_id>/output.pptx
  ├── copy spec.json, slide_plan.json, deck_definition.json
  ├── compute SHA-256 checksum for each
  ├── register ArtifactRecord in artifacts.db
  ├── write manifest.json
  └── finalize RunRecord in artifacts.db
```

Promotion is **non-fatal**: if individual files are missing they are skipped.
A run is only marked FAILED if `error_category` is explicitly passed to `promote()`.

---

## SQLite Databases

Both run and artifact registries share `artifacts.db` (separate from `jobs.db`):

- `runs` table — one row per `RunRecord`
- `artifacts` table — one or more rows per run

Both use WAL mode and `threading.Lock` for write serialization.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/runs/{run_id}` | Run metadata |
| `GET` | `/v1/runs/{run_id}/artifacts` | List artifacts for a run |
| `GET` | `/v1/runs/{run_id}/manifest` | Download manifest.json |
| `GET` | `/v1/artifacts/{artifact_id}/metadata` | Artifact metadata |
| `GET` | `/v1/artifacts/{artifact_id}/download` | Download file (PPTX only; 403 for internal) |

---

## Retention Policy

On server shutdown, `RetentionManager.run_cleanup()` scans `artifacts.db` for
artifacts older than their retention window, deletes the physical files, and marks
the database records as `expired`. The `always` class (manifest) is never expired.

---

## Configuration

| Env Var | Field | Default | Description |
|---|---|---|---|
| `PPTGEN_ARTIFACT_DB_PATH` | `artifact_db_path` | `{workspace_base}/artifacts.db` | SQLite registry |
| `PPTGEN_ARTIFACT_STORE_BASE` | `artifact_store_base` | `{workspace_base}/artifact_store` | Durable storage root |
| `PPTGEN_ARTIFACT_RETENTION_LONGEST_HOURS` | `artifact_retention_longest_hours` | `168` | PPTX retention (7 days) |
| `PPTGEN_ARTIFACT_RETENTION_MEDIUM_HOURS` | `artifact_retention_medium_hours` | `72` | Spec/plan/deck retention (3 days) |
| `PPTGEN_ARTIFACT_RETENTION_SHORTER_HOURS` | `artifact_retention_shorter_hours` | `24` | Log/diagnostic retention (1 day) |

---

## Source Files

| File | Purpose |
|---|---|
| `src/pptgen/runs/models.py` | `RunRecord`, `RunStatus`, `RunSource` |
| `src/pptgen/runs/store.py` | `AbstractRunStore` Protocol |
| `src/pptgen/runs/sqlite_store.py` | `SQLiteRunStore` |
| `src/pptgen/artifacts/models.py` | `ArtifactRecord`, `ArtifactType`, `ARTIFACT_POLICY` |
| `src/pptgen/artifacts/store.py` | `AbstractArtifactStore` Protocol |
| `src/pptgen/artifacts/sqlite_store.py` | `SQLiteArtifactStore` |
| `src/pptgen/artifacts/storage.py` | `ArtifactStorage`, `compute_checksum()` |
| `src/pptgen/artifacts/manifest.py` | `ManifestWriter` |
| `src/pptgen/artifacts/promoter.py` | `ArtifactPromoter` |
| `src/pptgen/artifacts/retention.py` | `RetentionManager` |
| `src/pptgen/api/run_routes.py` | Run inspection endpoints |
| `src/pptgen/api/artifact_routes.py` | Artifact download/metadata endpoints |
