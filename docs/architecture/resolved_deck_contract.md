# Resolved Deck Contract

**Status:** Stable
**Introduced:** Phase 9 Stage 4
**Last updated:** Phase 9 Stage 4

---

## 1. Purpose

The resolved deck is the complete state of the presentation after all pipeline
resolution stages have run. It consists of two complementary views:

1. **`deck_definition`** — the renderer-facing dict: the deck YAML structure
   with all token references substituted and all asset references replaced
   with inline dicts.

2. **`PipelineResult`** — the audit-facing record: the full pipeline output,
   containing `deck_definition` alongside every resolved intermediate structure
   produced during the run.

This document defines both views: what `deck_definition` contains when it
reaches the renderer, and what `PipelineResult` exposes to the caller.

---

## 2. Pipeline Execution Order

```
convert_spec_to_deck()
  ↓
Primitive Resolution   ← produces ResolvedSlidePrimitive (optional)
  ↓                      injects 'layout' + 'slots' into deck_definition
Layout Resolution      ← produces ResolvedLayout (optional)
  ↓                      validates slots; does not modify deck_definition
Token Resolution       ← produces ResolvedStyleMap (optional)
  ↓                      substitutes token.<key> refs in deck_definition
Asset Resolution       ← produces list[ResolvedAsset] (always runs)
  ↓                      replaces asset_id refs with inline dicts
Renderer               ← receives final deck_definition
```

Each resolution stage that runs modifies or validates `deck_definition` in
place before passing it to the next stage. The renderer receives the fully
resolved version.

---

## 3. `deck_definition` Structure

`deck_definition` is a plain Python `dict`. Its top-level structure is
produced by `convert_spec_to_deck()` and has the following shape:

```json
{
  "deck": {
    "title": "Q3 Business Review",
    "template": "executive",
    "author": "Strategy Team",
    "version": "1.0"
  },
  "slides": [
    {
      "type": "title",
      "id": "slide-1",
      "title": "Q3 Business Review",
      "subtitle": "September 2024",
      "notes": null,
      "visible": true
    },
    {
      "type": "bullets",
      "id": "slide-2",
      "title": "Key Results",
      "bullets": ["Revenue up 12%", "NPS at 68", "Churn below target"],
      "notes": null,
      "visible": true
    }
  ]
}
```

### Top-Level Keys

| Key | Type | Source |
|---|---|---|
| `deck` | object | `convert_spec_to_deck()` |
| `slides` | array | `convert_spec_to_deck()` |
| `layout` | string | Injected by primitive stage (if active) |
| `slots` | object | Injected by primitive stage (if active) |
| `primitive` | string | Present when template declares a primitive |
| `content` | object | Present when template declares a primitive |

The `layout`, `slots`, `primitive`, and `content` keys are only present when
the template uses the primitive system. Templates that go through the standard
`convert_spec_to_deck()` path produce only `deck` and `slides`.

### `deck` Object

| Key | Type | Guaranteed |
|---|---|---|
| `title` | string | yes |
| `template` | string | yes |
| `author` | string | yes |
| `version` | string (`"1.0"`) | yes |

### `slides` Array

Each slide entry is a dict with at minimum:

| Key | Type | Guaranteed |
|---|---|---|
| `type` | string (enum) | yes |
| `id` | string | yes |
| `notes` | string or null | yes |
| `visible` | boolean | yes |

The `type` field is one of: `"title"`, `"section"`, `"bullets"`,
`"two_column"`, `"metric_summary"`, `"image_caption"`.

Additional keys depend on the slide type. All slide types are produced by
`convert_spec_to_deck()` and validated by Pydantic slide models before the
pipeline stages run.

---

## 4. Renderer-Facing Guarantees

When `deck_definition` is passed to the renderer, the following guarantees
hold:

1. **No raw token references.** If a theme was resolved, all `token.<key>`
   string values in the deck have been substituted with resolved style values.
   The renderer will never see a string beginning with `token.`.

2. **No raw asset references.** All dicts with an `asset_id` key have been
   replaced with fully populated inline dicts containing `asset_id`,
   `resolved_source`, `type`, and `version`. The renderer will never see a
   raw `{"asset_id": "..."}` reference.

3. **`deck_definition` is a plain dict.** It contains only Python primitives
   (str, int, float, bool, None, list, dict). It is JSON-serializable.

4. **No design system objects.** The renderer does not receive and must not
   import any design system model class (`ResolvedLayout`, `ResolvedAsset`,
   etc.). All resolved structures are consumed by pipeline stages and stored
   separately in `PipelineResult`.

5. **Asset resolution always runs.** Even without a theme or primitive, the
   asset resolver traverses `deck_definition`. This is a no-op when no
   `asset_id` keys are present, but the guarantee is unconditional: the
   renderer will never receive unresolved asset references.

---

## 5. `PipelineResult` Contract

`PipelineResult` is a dataclass defined in
`src/pptgen/pipeline/generation_pipeline.py`. It is the return value of
`generate_presentation()`.

### Fields

| Field | Type | When set |
|---|---|---|
| `stage` | `"deck_planned"` or `"rendered"` | always |
| `playbook_id` | string | always |
| `input_text` | string | always |
| `mode` | string | always |
| `template_id` | string or None | always |
| `presentation_spec` | `PresentationSpec` or None | always |
| `slide_plan` | `SlidePlan` or None | always |
| `deck_definition` | dict or None | always |
| `output_path` | string or None | when rendered |
| `notes` | string | always (may be empty) |
| `artifact_paths` | dict or None | when `artifacts_dir` given |
| `resolved_style_map` | `ResolvedStyleMap` or None | when theme resolved |
| `resolved_layout` | `ResolvedLayout` or None | when layout resolved |
| `resolved_primitive` | `ResolvedSlidePrimitive` or None | when primitive resolved |
| `resolved_assets` | list[`ResolvedAsset`] or None | always (after asset stage) |

### Stage Values

- `"deck_planned"` — `output_path` was not provided; no file was written.
- `"rendered"` — `output_path` was provided; a `.pptx` file was written.

### Resolved Structure Fields

`resolved_style_map`, `resolved_layout`, `resolved_primitive`, and
`resolved_assets` are `None` when their respective stages did not run:

- `resolved_style_map` is `None` when no theme was active.
- `resolved_layout` is `None` when the deck declares no `layout` key.
- `resolved_primitive` is `None` when the deck declares no `primitive` key.
- `resolved_assets` is `None` when the asset resolution stage did not run
  (i.e. `deck_definition` is not a dict). In practice this means it is an
  empty list `[]` for all normal runs with a valid deck_definition; `None`
  only occurs if `deck_definition` itself is `None`.

When `resolved_assets` is an empty list, no asset references were present in
the deck. When it is a non-empty list, each entry is a `ResolvedAsset`
instance in first-occurrence order.

---

## 6. Layering of Resolution Stages

The four resolution stages are independent in their outputs but sequential in
their application to `deck_definition`:

```
Stage           Reads from           Writes to
─────────────── ──────────────────── ─────────────────────────────────────────
Primitive       deck_definition      deck_definition (injects layout + slots)
                                     PipelineResult.resolved_primitive

Layout          deck_definition      (no mutation — validation only)
                                     PipelineResult.resolved_layout

Token           deck_definition      deck_definition (token refs substituted)
                                     PipelineResult.resolved_style_map

Asset           deck_definition      deck_definition (asset refs replaced)
                                     PipelineResult.resolved_assets
```

The layout stage is the only stage that does not modify `deck_definition`. It
reads `deck_definition["layout"]` and `deck_definition["slots"]`, validates
them, and stores the result in `PipelineResult.resolved_layout` without
writing back to the dict.

---

## 7. Failure Semantics

All failures raise immediately. Silent fallback is prohibited.

| Stage | Exception type | Wrapped as |
|---|---|---|
| Primitive resolution | `DesignSystemError` subclass | `PipelineError` |
| Layout resolution | `DesignSystemError` subclass | `PipelineError` |
| Token resolution | `DesignSystemError` subclass | `PipelineError` |
| Asset resolution | `DesignSystemError` subclass | `PipelineError` |
| Rendering | `PptgenError` | `PipelineError` |
| Artifact export | `OSError` | `PipelineError` |

When any stage fails, `generate_presentation()` raises `PipelineError` and
returns no `PipelineResult`. There is no partial result.

---

## 8. Artifact Paths Contract

When `artifacts_dir` is provided, `PipelineResult.artifact_paths` is a dict
mapping artifact names to absolute file path strings.

### Always Written (when `artifacts_dir` is given)

| Key | File | Contents |
|---|---|---|
| `"spec"` | `spec.json` | `PresentationSpec.model_dump()` |
| `"slide_plan"` | `slide_plan.json` | `dataclasses.asdict(SlidePlan)` |
| `"deck_definition"` | `deck_definition.json` | Final resolved `deck_definition` |

### Written Conditionally

| Key | File | Written when |
|---|---|---|
| `"resolved_theme_snapshot"` | `resolved_theme_snapshot.json` | `resolved_style_map` is not None |
| `"resolved_layout_snapshot"` | `resolved_layout_snapshot.json` | `resolved_layout` is not None |
| `"resolved_primitive_snapshot"` | `resolved_primitive_snapshot.json` | `resolved_primitive` is not None |
| `"resolved_assets_snapshot"` | `resolved_assets_snapshot.json` | `resolved_assets` is a non-empty list |

The `deck_definition.json` artifact is the final resolved deck — it contains
substituted token values and inline asset dicts, exactly as the renderer
receives it.

---

## 9. Determinism Guarantees

1. **Same input → same deck_definition.** Given the same `input_text`,
   `template_id`, `mode`, `theme_id`, and the same artifacts on disk, every
   call to `generate_presentation()` produces an identical `deck_definition`.

2. **Stage independence.** Each resolution stage is deterministic
   independently. The combined output is deterministic because each stage is.

3. **Asset resolution is a pure function of the deck.** The same
   `deck_definition` with the same registry on disk always produces the same
   resolved deck and the same `resolved_assets` list.

4. **No cross-run state.** The asset deduplication index, the token resolver,
   and the primitive resolver do not retain state between calls to
   `generate_presentation()`. Each call starts fresh.

---

## 10. Stability Statement

This contract is considered stable as of Phase 9 Stage 4.

The `PipelineResult` field names and their types must not change without a
migration. Specifically:

- `deck_definition` always contains the fully resolved deck as a plain dict.
- `resolved_style_map`, `resolved_layout`, `resolved_primitive`, and
  `resolved_assets` are always typed as documented (None or the concrete type).
- `artifact_paths` keys are stable identifiers that downstream tools may
  depend on.
- The `stage` field is always one of the two documented string values.

New fields may be added to `PipelineResult` in a backward-compatible way.
Existing fields must not be removed or renamed.
