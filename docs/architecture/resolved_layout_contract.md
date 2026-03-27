# Resolved Layout Contract

**Status:** Stable
**Introduced:** Phase 9 Stage 2
**Last updated:** Phase 9 Stage 2

---

## 1. Purpose

A resolved layout is the output of the layout resolution stage. It captures
the identity of the layout that was declared, the full set of region
definitions that layout defines, and the slot names that were validated
against those regions.

Layouts define structure only — content regions, positioning metadata, and
slot constraints. They carry no slide semantics, styling, or token overrides.
The `ResolvedLayout` is the concrete record of the validation pass, confirming
that the template's slot declarations satisfy the layout's requirements.

Position in pipeline:

```
convert_spec_to_deck()
  ↓
Primitive Resolution   ← may inject 'layout' and 'slots' into deck_definition
  ↓
Layout Resolution      ← produces ResolvedLayout
  ↓                      validates provided_slots against region definitions
Token Resolution
  ↓
Asset Resolution
  ↓
Renderer
```

The resolved layout is stored in `PipelineResult.resolved_layout` and, when
`artifacts_dir` is provided, persisted to `resolved_layout_snapshot.json`.

---

## 2. Contract Definition (Authoritative)

`ResolvedLayout` is a frozen dataclass defined in
`src/pptgen/design_system/layout_models.py`. It has exactly four fields.
All four are always present.

The `to_dict()` method produces the following structure:

```json
{
  "layout_id": "two_column",
  "layout_version": "1.0.0",
  "regions": {
    "left": {
      "required": true,
      "label": "Left Column",
      "position": {"x": 5, "y": 15, "width": 42, "height": 80}
    },
    "right": {
      "required": true,
      "label": "Right Column",
      "position": {"x": 53, "y": 15, "width": 42, "height": 80}
    }
  },
  "provided_slots": ["left", "right"]
}
```

For a single-region layout:

```json
{
  "layout_id": "single_column",
  "layout_version": "1.0.0",
  "regions": {
    "content": {
      "required": true,
      "label": "Main Content",
      "position": {"x": 5, "y": 15, "width": 90, "height": 80}
    }
  },
  "provided_slots": ["content"]
}
```

### Field Summary

| Field | Type | Required |
|---|---|---|
| `layout_id` | string | yes |
| `layout_version` | string | yes |
| `regions` | object | yes |
| `provided_slots` | array of strings | yes |

---

## 3. Field Semantics

### `layout_id`

- **Type:** string
- **Meaning:** The stable identifier of the layout that was resolved. Matches
  the `layout_id` field of the `LayoutDefinition` YAML and the filename stem
  under `design_system/layouts/`.
- **Guarantees:** Always identical to the value declared in the template's
  `layout` key (or injected by the primitive stage). Never transformed or
  aliased.

### `layout_version`

- **Type:** string
- **Meaning:** The version string from the matching layout YAML artifact
  (e.g. `"1.0.0"`). Records which version of the definition was active at
  resolution time.
- **Guarantees:** Copied verbatim from the YAML definition.

### `regions`

- **Type:** `dict[str, object]`
- **Meaning:** The full set of region definitions from the resolved layout,
  keyed by region name. Contains every region declared in the layout YAML,
  not just the regions that were provided by the template.
- **Structure:** Each region value has exactly three keys:

  | Key | Type | Meaning |
  |---|---|---|
  | `required` | boolean | Whether the template must provide this region |
  | `label` | string | Human-readable description (may be empty string) |
  | `position` | object | Positioning metadata (may be empty object) |

- **Guarantees:**
  - Always includes all regions from the layout definition, regardless of
    which slots the template provided.
  - `required` is always a boolean (never absent, never null).
  - `label` is always a string (empty string when not declared in the YAML).
  - `position` is always a dict (empty dict when not declared in the YAML).
  - The dict keys in `position` (e.g. `x`, `y`, `width`, `height`) are
    informational and determined by the YAML author. The pipeline treats
    them as opaque.

### `provided_slots`

- **Type:** array of strings
- **Meaning:** The slot names that the template declared, in the order they
  appeared in `deck_definition["slots"]`. These are the names that were
  validated against the layout's region definitions.
- **Guarantees:**
  - All names in this list passed validation — they either match a defined
    region or the layout declares `allow_extra_slots: true`.
  - All required regions are represented somewhere in this list (or
    resolution would have failed).
  - Order is preserved from the input slot declaration; it is not sorted.
  - The list may be a subset of `regions` keys (when optional regions are
    not provided).

---

## 4. Resolution Guarantees

1. **Deterministic.** Given the same `layout_id`, the same layout YAML on
   disk, and the same `provided_slots` list, resolution always produces the
   same `ResolvedLayout`.

2. **Layout version is fixed by the YAML.** `layout_version` comes
   exclusively from the YAML definition. Templates cannot override it.

3. **All required regions are validated before resolution completes.** If any
   required region is absent from `provided_slots`, resolution fails before a
   `ResolvedLayout` is produced.

4. **Unknown slots are rejected by default.** Unless the layout declares
   `allow_extra_slots: true`, any slot name not matching a defined region
   raises an error.

5. **`regions` reflects the full layout definition.** The region dict is
   taken directly from the loaded `LayoutDefinition`. Regions not supplied by
   the template are still present in `regions`.

6. **No mutation after production.** Once produced, the `ResolvedLayout` is
   not modified by any downstream stage.

---

## 5. Failure Semantics

All failures raise immediately. Silent fallback is prohibited.

| Condition | Exception |
|---|---|
| `layout_id` not found in registry | `UnknownLayoutError` |
| Layout YAML is malformed or missing required keys | `InvalidLayoutDefinitionError` |
| Required region not in `provided_slots` | `MissingRequiredSlotError` |
| Slot name not in layout regions (when `allow_extra_slots=false`) | `UnknownSlotError` |

All exceptions inherit from `DesignSystemError`. The pipeline wraps them as
`PipelineError` before they reach the caller. There is no partial resolution.

---

## 6. Pipeline Trigger

Layout resolution runs when `deck_definition` contains a non-empty `layout`
key. The value of that key is passed as `layout_id` to the resolver.

Templates that do not declare a `layout` key are unaffected. In those cases
`PipelineResult.resolved_layout` is `None`.

When the primitive stage runs before layout resolution, it injects
`deck_definition["layout"]` from the primitive's `layout_id` field. The
layout stage then processes that injected value identically to a manually
declared layout.

---

## 7. Snapshot Contract

When `artifacts_dir` is provided and a layout was resolved, the file
`<artifacts_dir>/resolved_layout_snapshot.json` is written. The snapshot is
produced by `to_dict()` and has the structure shown in Section 2.

The path is recorded in `PipelineResult.artifact_paths` under the key
`"resolved_layout_snapshot"`.

The snapshot is written if and only if `resolved_layout` is not `None`. If
no layout was declared, no file is written.

---

## 8. Stability Statement

This contract is considered stable as of Phase 9 Stage 2.

The four fields of `ResolvedLayout` (`layout_id`, `layout_version`,
`regions`, `provided_slots`) and the structure of each region value
(`required`, `label`, `position`) must not change without a versioned
migration.
