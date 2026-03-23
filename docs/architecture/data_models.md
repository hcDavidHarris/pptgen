# Data Models Reference

Version: 1.0
See also: [system_overview.md](system_overview.md) for the pipeline narrative.

---

## Pipeline Model Flow

```
Input Text
    │
    ▼  (connectors only)
ConnectorOutput          src/pptgen/connectors/base_connector.py
    │
    ▼
PresentationSpec         src/pptgen/spec/presentation_spec.py
    │   (semantic content — what to say)
    ▼
SlidePlan                src/pptgen/planner/slide_plan.py
    │   (observability — how many slides, what types)
    ▼
deck_definition (dict)   src/pptgen/spec/spec_to_deck.py
    │   (structural layout — maps to YAML schema)
    ▼
.pptx file               src/pptgen/render/deck_renderer.py

All stages wrapped in ── PipelineResult   src/pptgen/pipeline/generation_pipeline.py
Batch runs wrapped in ── BatchResult      src/pptgen/orchestration/batch_generator.py
```

---

## Cross-Reference

| Model | Produced by | Consumed by | Source |
|---|---|---|---|
| `ConnectorOutput` | `connector.normalize(path)` | `generate_presentation()` | `connectors/base_connector.py` |
| `PresentationSpec` | `execute_playbook_full()` | `plan_slides()`, `convert_spec_to_deck()` | `spec/presentation_spec.py` |
| `SlidePlan` | `plan_slides()` | `PipelineResult`, API response | `planner/slide_plan.py` |
| `deck_definition` | `convert_spec_to_deck()` | `render_deck()`, artifact export | `spec/spec_to_deck.py` |
| `PipelineResult` | `generate_presentation()` | CLI, API service layer | `pipeline/generation_pipeline.py` |
| `BatchResult` | `BatchGenerator.run()` | `generate-batch` CLI | `orchestration/batch_generator.py` |

---

## PresentationSpec

**Source:** `src/pptgen/spec/presentation_spec.py`
**Implementation:** Pydantic v2, `extra='forbid'`
**Purpose:** Semantic description of a full presentation. Describes *what* to communicate,
not how slides are laid out. Produced by the playbook engine from raw input text.

| Field | Type | Default | Description |
|---|---|---|---|
| `title` | `str` | required | Presentation title |
| `subtitle` | `str` | required | Context line or subtitle |
| `author` | `str` | `"Unknown"` | Author name (written to deck metadata) |
| `template` | `str` | `"ops_review_v1"` | Template ID — must be registered in `templates/registry.yaml` |
| `sections` | `list[SectionSpec]` | `[]` | Ordered list of content sections |

### SectionSpec

| Field | Type | Default | Description |
|---|---|---|---|
| `title` | `str` | required | Section heading |
| `bullets` | `list[str]` | `[]` | Bullet points (max 6 per generated slide) |
| `metrics` | `list[MetricSpec]` | `[]` | KPI values (max 4 per generated metric_summary slide) |
| `images` | `list[ImageSpec]` | `[]` | Diagrams or screenshots (one image_caption slide each) |
| `include_section_divider` | `bool` | `True` | When `True`, emit a section slide before section content |

### MetricSpec

| Field | Type | Default | Description |
|---|---|---|---|
| `label` | `str` | required | Short metric name (≤40 chars recommended) |
| `value` | `str` | required | Metric value (e.g. `"99.2%"`, `"14"`) |
| `unit` | `str \| None` | `None` | Optional unit suffix (e.g. `" ms"`) appended to value |

### ImageSpec

| Field | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | Relative or absolute path to a PNG or JPEG file |
| `caption` | `str` | required | Explanatory text displayed on the slide |
| `title` | `str \| None` | `None` | Slide title override. Defaults to parent section title. |

---

## SlidePlan

**Source:** `src/pptgen/planner/slide_plan.py`
**Implementation:** Python dataclass (not Pydantic)
**Purpose:** Lightweight planning summary produced by `plan_slides()`. Useful for
observability, debugging, and testing the planner independently of the renderer.
Not rendered directly — `deck_definition` is what the renderer uses.

| Field | Type | Default | Description |
|---|---|---|---|
| `playbook_id` | `str \| None` | required | Playbook that produced the source spec |
| `slide_count` | `int` | required | Total number of planned slides |
| `planned_slide_types` | `list[str]` | required | Ordered slide type strings (e.g. `["title", "section", "bullets"]`) |
| `section_count` | `int` | required | Number of sections in the source `PresentationSpec` |
| `slides` | `list[PlannedSlide]` | `[]` | Per-slide planning entries |
| `notes` | `str` | `""` | Optional diagnostic notes from the planner |

### PlannedSlide

| Field | Type | Default | Description |
|---|---|---|---|
| `slide_type` | `str` | required | Slide type string (e.g. `"title"`, `"bullets"`) |
| `title` | `str` | required | Slide title derived from the spec |
| `source_section_title` | `str \| None` | `None` | Source section title, or `None` for the title slide |

---

## deck_definition

**Source:** `src/pptgen/spec/spec_to_deck.py` — `convert_spec_to_deck(spec) -> dict`
**Implementation:** Plain `dict[str, Any]` — not a typed class
**Purpose:** Structural layout of the deck, matching the pptgen YAML schema. This is
what `render_deck()` consumes and what is written to `deck_definition.json` when
artifacts are exported. Can be round-tripped through `yaml.dump()` / `yaml_loader`.

```python
{
    "deck": {
        "title":    str,       # spec.title
        "template": str,       # spec.template
        "author":   str,       # spec.author
        "version":  "1.0",
    },
    "slides": [
        {"type": "title",    "title": str, "subtitle": str},
        {"type": "section",  "id": str, "section_title": str},
        {"type": "bullets",  "id": str, "title": str, "bullets": [str, ...]},
        {"type": "metric_summary", "id": str, "title": str,
         "metrics": [{"label": str, "value": str, "unit": str | None}, ...]},
        {"type": "image_caption", "id": str, "title": str,
         "image_path": str, "caption": str},
    ]
}
```

The structure matches the validated `DeckFile` / `SlideUnion` Pydantic models
in `src/pptgen/models/`. See [YAML Authoring Models](#yaml-authoring-models) below.

---

## PipelineResult

**Source:** `src/pptgen/pipeline/generation_pipeline.py`
**Implementation:** Python dataclass
**Purpose:** Structured result returned by `generate_presentation()`. Contains all
intermediate and final outputs. Returned to the CLI, API service layer, and tests.

| Field | Type | Default | Description |
|---|---|---|---|
| `stage` | `str` | required | `"rendered"` or `"deck_planned"` (preview only) |
| `playbook_id` | `str` | required | Playbook selected by the input router |
| `input_text` | `str` | required | The normalised input text that was processed |
| `mode` | `str` | `"deterministic"` | Execution mode: `"deterministic"` or `"ai"` |
| `template_id` | `str \| None` | `None` | Template ID used for rendering |
| `presentation_spec` | `PresentationSpec \| None` | `None` | Extracted spec |
| `slide_plan` | `SlidePlan \| None` | `None` | Slide plan from the planner |
| `deck_definition` | `dict \| None` | `None` | Deck dict from the translator |
| `output_path` | `str \| None` | `None` | Absolute path to the `.pptx` file. `None` = preview only. |
| `notes` | `str` | `""` | Optional diagnostic notes from the pipeline |
| `artifact_paths` | `dict[str, str] \| None` | `None` | Artifact name → file path mapping |

`stage="deck_planned"` and `output_path=None` together indicate preview mode —
`generate_presentation()` was called with `output_path=None`.

---

## ConnectorOutput

**Source:** `src/pptgen/connectors/base_connector.py`
**Implementation:** Python dataclass
**Purpose:** Return value of `connector.normalize(path)`. Carries pipeline-ready
text alongside optional structured metadata extracted from the source file.

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | required | Normalised text ready for `generate_presentation()` |
| `metadata` | `dict[str, Any]` | `{}` | Optional structured fields (e.g. sprint name, team, period) |

The `Connector` protocol (also in `base_connector.py`) is a structural interface
requiring `normalize(path: Path) -> ConnectorOutput`. No network access — local files only.

---

## BatchResult / BatchItemResult

**Source:** `src/pptgen/orchestration/batch_generator.py`
**Implementation:** Python dataclasses
**Purpose:** Aggregate results from `BatchGenerator.run()`, which processes every
file in a directory through `generate_presentation()`. Used by `pptgen generate-batch`.

### BatchResult

| Field | Type | Default | Description |
|---|---|---|---|
| `total_files` | `int` | required | Files discovered in the input directory |
| `succeeded` | `int` | required | Files processed without error |
| `failed` | `int` | required | Files that produced an error |
| `outputs` | `list[BatchItemResult]` | `[]` | Per-file results in processing order |
| `notes` | `list[str]` | `[]` | Diagnostic notes (e.g. skipped subdirectories) |

### BatchItemResult

| Field | Type | Default | Description |
|---|---|---|---|
| `input_path` | `Path` | required | Source file that was processed |
| `output_path` | `Path \| None` | `None` | Rendered `.pptx` path, or `None` on failure |
| `playbook_id` | `str \| None` | `None` | Playbook chosen, or `None` on failure |
| `success` | `bool` | `False` | Whether the file was processed without error |
| `error` | `str` | `""` | Error message if `success` is `False` |
| `artifact_paths` | `dict[str, str] \| None` | `None` | Artifact paths if exported |

---

## YAML Authoring Models

`src/pptgen/models/deck.py` and `src/pptgen/models/slides.py` contain `DeckFile`,
`DeckMetadata`, and `SlideUnion` — the Pydantic models used to **validate deck YAML
files that are authored directly** (e.g. with `pptgen build --input deck.yaml`).

These are **separate from** the pipeline models above. When the pipeline runs,
`convert_spec_to_deck()` produces a `deck_definition` dict that matches this schema,
but the pipeline never explicitly instantiates `DeckFile`.

For teams authoring deck YAML directly, see
[docs/authoring/yaml_authoring_guide.md](../authoring/yaml_authoring_guide.md) and
[docs/authoring/slide_type_reference.md](../authoring/slide_type_reference.md).
