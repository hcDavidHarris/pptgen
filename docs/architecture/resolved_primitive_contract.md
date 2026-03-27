# Resolved Primitive Contract

**Status:** Stable
**Introduced:** Phase 9 Stage 3
**Last updated:** Phase 9 Stage 3

---

## 1. Purpose

A resolved primitive is the output of the primitive resolution stage. It
captures the identity of the primitive that was declared, validates the
semantic content provided by the template, and produces a layout-ready slot
structure that the layout resolution stage consumes.

Primitives map semantic intent to layout structure. A `bullet_slide` primitive
does not know how bullets look — it knows that a `bullets` field maps to a
`content` region. The `ResolvedSlidePrimitive` is the concrete record of that
mapping after validation.

Position in pipeline:

```
convert_spec_to_deck()
  ↓
Primitive Resolution   ← produces ResolvedSlidePrimitive
  ↓                      injects layout + slots into deck_definition
Layout Resolution
  ↓
Token Resolution
  ↓
Asset Resolution
  ↓
Renderer
```

The resolved primitive is stored in `PipelineResult.resolved_primitive` and,
when `artifacts_dir` is provided, persisted to
`resolved_primitive_snapshot.json`.

---

## 2. Contract Definition (Authoritative)

`ResolvedSlidePrimitive` is a frozen dataclass defined in
`src/pptgen/design_system/primitive_models.py`. It has exactly four fields.
All four are always present.

The `to_dict()` method produces the following structure:

```json
{
  "primitive_id": "bullet_slide",
  "primitive_version": "1.0.0",
  "layout_id": "single_column",
  "resolved_slots": {
    "content": {
      "title": "Q3 Performance",
      "bullets": ["Revenue up 12%", "NPS at 68", "Churn below target"]
    }
  }
}
```

For a two-region primitive:

```json
{
  "primitive_id": "comparison_slide",
  "primitive_version": "1.0.0",
  "layout_id": "two_column",
  "resolved_slots": {
    "left": {
      "left": {"title": "Option A", "points": ["Lower cost", "Faster setup"]}
    },
    "right": {
      "right": {"title": "Option B", "points": ["More scalable", "Better support"]}
    }
  }
}
```

### Field Summary

| Field | Type | Required |
|---|---|---|
| `primitive_id` | string | yes |
| `primitive_version` | string | yes |
| `layout_id` | string | yes |
| `resolved_slots` | object | yes |

---

## 3. Field Semantics

### `primitive_id`

- **Type:** string
- **Meaning:** The stable identifier of the primitive that was resolved.
  Matches the `primitive_id` field of the `SlidePrimitiveDefinition` YAML and
  the filename stem under `design_system/primitives/`.
- **Guarantees:** Always identical to the value declared in the template's
  `primitive` key. Never transformed or aliased.

### `primitive_version`

- **Type:** string
- **Meaning:** The version string from the matching primitive YAML artifact
  (e.g. `"1.0.0"`). Records which version of the definition was active at
  resolution time.
- **Guarantees:** Copied verbatim from the YAML definition.

### `layout_id`

- **Type:** string
- **Meaning:** The layout this primitive maps to, taken directly from the
  primitive's `layout_id` field. This value is injected into
  `deck_definition["layout"]` after resolution so the layout stage processes
  it automatically.
- **Guarantees:** Always a non-empty string. Always the exact value declared
  in the primitive YAML, never overridden by the template.

### `resolved_slots`

- **Type:** `dict[str, dict[str, Any]]`
- **Meaning:** Content grouped by layout region. Each top-level key is a
  layout region name (matching a region defined in the layout identified by
  `layout_id`). Each value is a dict of `{field_name: value}` pairs drawn
  from the template's `content` block, after type validation.
- **Structure:** `{region_name: {content_field_name: content_value, ...}, ...}`
- **Guarantees:**
  - Every top-level key is the `maps_to` value from the matched `SlotDefinition`.
  - Content fields that map to the same region are merged into a single dict
    under that region key.
  - Only fields present in the template's `content` block appear. Optional
    fields omitted by the template are absent from `resolved_slots`.
  - Values are the exact values from `content`, post type-validation but
    otherwise unchanged. No transformation is applied.
- **Pipeline use:** This dict is injected verbatim as `deck_definition["slots"]`
  after resolution, making it immediately consumable by the layout stage.

---

## 4. Resolution Guarantees

1. **Deterministic slot mapping.** Given the same `primitive_id`, the same
   primitive YAML on disk, and the same `content` dict, resolution always
   produces the same `resolved_slots` structure.

2. **Layout is fixed by the primitive.** The `layout_id` in
   `ResolvedSlidePrimitive` comes exclusively from the primitive definition.
   Templates cannot override it.

3. **All required content fields are validated before resolution completes.**
   If any required field is absent, resolution fails before a
   `ResolvedSlidePrimitive` is produced.

4. **No implicit slot generation.** Only fields explicitly present in
   `content` appear in `resolved_slots`. Fields declared as optional but not
   provided by the template produce no entry.

5. **Type validation is enforced.** Each content field is checked against
   its declared `content_type` (`"string"`, `"list"`, `"dict"`, `"number"`,
   `"any"`). A mismatch fails resolution.

6. **Unknown content fields are rejected by default.** Unless the primitive
   declares `allow_extra_content: true`, any field in `content` not declared
   in the primitive's `slots` raises an error.

---

## 5. Failure Semantics

All failures raise immediately. Silent fallback is prohibited.

| Condition | Exception |
|---|---|
| `primitive_id` not found in registry | `UnknownPrimitiveError` |
| Primitive YAML is malformed or missing required keys | `InvalidPrimitiveDefinitionError` |
| Required content field not provided | `MissingRequiredContentError` |
| Content field not declared in primitive slots (when `allow_extra_content=false`) | `UnknownContentFieldError` |
| Content field value does not match declared `content_type` | `InvalidContentTypeError` |

All exceptions inherit from `DesignSystemError`. The pipeline wraps them as
`PipelineError` before they reach the caller. There is no partial resolution.

---

## 6. Output Guarantees

1. **Output is layout-ready.** `resolved_slots` keys are layout region names.
   The layout resolver can consume them directly after injection into
   `deck_definition["slots"]`.

2. **No renderer-specific logic.** `ResolvedSlidePrimitive` carries no
   rendering instructions, style values, positioning data, or template
   references.

3. **Stable structure within a run.** Once produced, the
   `ResolvedSlidePrimitive` is not modified by any downstream stage.

4. **`layout_id` injected into pipeline.** After resolution, the pipeline
   sets `deck_definition["layout"] = resolved_primitive.layout_id` and
   `deck_definition["slots"] = resolved_primitive.resolved_slots` before
   passing to the layout stage.

---

## 7. Snapshot Contract

When `artifacts_dir` is provided, the file
`<artifacts_dir>/resolved_primitive_snapshot.json` is written if and only if
a primitive was resolved. The snapshot is produced by `to_dict()` and has
the structure shown in Section 2.

The path is recorded in `PipelineResult.artifact_paths` under the key
`"resolved_primitive_snapshot"`.

---

## 8. Stability Statement

This contract is considered stable as of Phase 9 Stage 3.

The four fields of `ResolvedSlidePrimitive` (`primitive_id`,
`primitive_version`, `layout_id`, `resolved_slots`) and the structure of
`resolved_slots` must not change without a versioned migration. The
`resolved_slots` nesting shape — `{region: {field: value}}` — is load-bearing
for the layout injection step and must remain stable.
