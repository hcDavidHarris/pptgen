# Asset Inline Contract

**Status:** Stable
**Introduced:** Phase 9 Stage 4
**Last updated:** Phase 9 Stage 4

---

## 1. Purpose

The asset inline contract defines the exact structure of a resolved asset object
as it appears inside a deck definition after the asset resolution pipeline stage.

An asset reference in template content is a plain dict containing a single key,
`asset_id`. The asset resolver replaces this reference with a resolved inline
dict before the deck definition reaches the renderer. The renderer never sees
raw references and never queries the asset registry.

This contract sits between the asset resolution stage and the rendering stage:

```
Primitive Resolution
  ↓
Layout Resolution
  ↓
Token Resolution
  ↓
Asset Resolution   ← references replaced with inline dicts defined here
  ↓
Renderer           ← receives resolved inline dicts; this contract is its input
```

The contract exists so the renderer, tests, and any downstream consumers have
a single unambiguous definition of what a resolved asset looks like.

---

## 2. Contract Definition (Authoritative)

A resolved asset inline dict has exactly four fields. All four are always
present. No field is optional.

```json
{
  "asset_id": "icon.check",
  "resolved_source": "assets/icons/check.svg",
  "type": "icon",
  "version": "1.0.0"
}
```

This structure is produced by `ResolvedAsset.as_inline()` in
`src/pptgen/design_system/asset_models.py`. That method is the authoritative
source of the inline shape. This document reflects it exactly.

### Field Summary

| Field | Type | Required |
|---|---|---|
| `asset_id` | string | yes |
| `resolved_source` | string | yes |
| `type` | string (enum) | yes |
| `version` | string | yes |

No other fields appear in the inline dict. Consumers must not depend on fields
beyond these four.

---

## 3. Field Semantics

### `asset_id`

- **Type:** string
- **Meaning:** The original reference identifier as written in template content.
  Matches the `asset_id` field of the `AssetDefinition` YAML and the filename
  stem under `design_system/assets/`.
- **Guarantees:** Always preserved from the original reference. Never
  transformed, normalised, or aliased. The value in the inline dict is
  identical to the value that was written in the template.

### `resolved_source`

- **Type:** string
- **Meaning:** The `source` value from the matching `AssetDefinition`. A path
  or URI pointing to the asset file. The platform treats this string as opaque;
  it is copied directly from the registry definition without modification.
- **Guarantees:** Determined entirely by the YAML config artifact. Identical
  for the same `asset_id` across all runs against the same registry. The
  renderer is responsible for interpreting this string relative to its own
  working directory.

### `type`

- **Type:** string, constrained enum
- **Allowed values:** `"icon"`, `"image"`, `"logo"`
- **Meaning:** The asset category as declared in the `AssetDefinition`. Used
  by the renderer to determine how to handle the asset.
- **Guarantees:** Always one of the three allowed values. Any asset definition
  with a `type` outside this set fails at registry load time with
  `InvalidAssetTypeError` — it cannot reach the inline stage.

### `version`

- **Type:** string
- **Meaning:** The version string from the matching `AssetDefinition`
  (e.g. `"1.0.0"`). Identifies which version of the config artifact was active
  at resolution time.
- **Guarantees:** Copied verbatim from the YAML definition. Present on every
  inline dict regardless of whether the consumer uses it.

---

## 4. Resolution Guarantees

The following are hard guarantees upheld by the asset resolution stage:

1. **`asset_id` is always preserved.** The inline dict always contains the
   original `asset_id` value. It is never removed or renamed.

2. **Resolution is deterministic.** Given the same `asset_id` and the same
   registry on disk, resolution always produces the same inline dict.

3. **Same `asset_id` → same resolved output.** All occurrences of the same
   `asset_id` in a single deck definition resolve to identical inline dicts.
   There is no per-occurrence variation.

4. **Resolution happens before rendering.** The renderer is called only after
   asset resolution completes. The renderer never receives a raw `asset_id`
   reference dict.

5. **The resolved inline dict is stable within a run.** Once produced, the
   inline dict is not modified by any subsequent pipeline stage. Token
   resolution runs before asset resolution; assets do not contain token
   references and token resolution does not process asset inline dicts.

6. **Resolution is a no-op when no references are present.** Deck definitions
   with no `asset_id` keys pass through the resolver unchanged. No side effects
   occur.

---

## 5. Renderer Contract

The renderer can depend on the following:

- Every `asset_id` reference in the deck definition has been replaced by a
  resolved inline dict before the renderer is called.
- The resolved inline dict always contains all four fields defined in
  Section 2. No field will be absent.
- The `type` field is always one of `"icon"`, `"image"`, `"logo"`.
- The renderer does not need to, and must not, query the asset registry.
- The renderer must treat the inline dict as an opaque input. It must read
  the fields but must not modify, augment, or remove them.
- The `resolved_source` value is a path or URI string. The renderer is
  responsible for resolving it relative to its working directory. The platform
  makes no guarantee about whether the file at that path exists at render time.

---

## 6. Failure Semantics

All failures raise immediately. Silent fallback is prohibited.

| Condition | Exception | Raised by |
|---|---|---|
| `asset_id` value not found in registry | `UnknownAssetError` | `AssetResolver` |
| `asset_id` value is empty or not a string | `UnknownAssetError` | `AssetResolver` |
| Asset YAML file is malformed or missing required keys | `InvalidAssetDefinitionError` | `DesignSystemRegistry.get_asset()` |
| Asset YAML declares a `type` not in the allowed set | `InvalidAssetTypeError` | `DesignSystemRegistry.get_asset()` |

All three exception types inherit from `DesignSystemError`. The pipeline
wraps them as `PipelineError` before they reach the caller.

There is no partial resolution. If any reference in the deck fails, the
entire pipeline run fails.

---

## 7. Deduplication Behavior

The resolver maintains an in-memory index keyed by `asset_id` for the duration
of a single resolution pass.

- Each unique `asset_id` is looked up in the registry exactly once per pass,
  regardless of how many times it appears in the deck definition.
- Every occurrence of the same `asset_id` in the deck receives an identical
  inline dict (same object values; not the same Python object).
- The `resolved_assets` list in `PipelineResult` contains each unique
  `asset_id` exactly once, in order of first occurrence in the deck definition.
- The deduplication index is not shared across pipeline runs. Each call to
  `generate_presentation()` starts a fresh index.

---

## 8. Snapshot Contract

When `artifacts_dir` is provided and at least one asset reference was resolved,
the pipeline writes:

```
<artifacts_dir>/resolved_assets_snapshot.json
```

### Structure

```json
{
  "assets": [
    {
      "asset_id": "icon.check",
      "version": "1.0.0",
      "type": "icon",
      "resolved_source": "assets/icons/check.svg"
    },
    {
      "asset_id": "logo.company",
      "version": "1.0.0",
      "type": "logo",
      "resolved_source": "assets/logos/company.svg"
    }
  ]
}
```

The snapshot is produced by `ResolvedAsset.to_dict()`. The four fields it
contains (`asset_id`, `version`, `type`, `resolved_source`) are identical
to the four fields in the inline dict (Section 2).

### Snapshot Guarantees

- The file is only written when `resolved_assets` is a non-empty list. If no
  asset references were present in the deck, no file is written.
- The `assets` array contains one entry per unique `asset_id`, in order of
  first occurrence.
- The array order does not imply rendering order.
- The snapshot is for audit and debugging. It is not read by any pipeline stage
  and has no effect on rendering.
- The snapshot path is recorded in `PipelineResult.artifact_paths` under the
  key `"resolved_assets_snapshot"`.

---

## 9. Out of Scope

The following are explicitly not part of this contract and are not implemented:

- **Asset transformation.** The platform does not resize, recolour, crop, or
  otherwise modify asset files.
- **Asset variant selection.** There is no logic to choose between light/dark,
  high-DPI, or locale-specific variants.
- **CDN or remote resolution.** `resolved_source` is copied verbatim from the
  config artifact. The platform performs no HTTP requests.
- **Dynamic asset selection.** Asset lookup is always by exact `asset_id`.
  There is no pattern matching, fallback chain, or runtime selection logic.
- **Chart rendering.** The `type` enum does not include `"chart"`. Chart
  artifacts are not part of the asset system.
- **Style application.** The asset system applies no colours, sizes, or
  typographic properties to assets.
- **Metadata passthrough.** The `metadata` field from `AssetDefinition` is not
  included in the inline dict and is not passed to the renderer.
- **Renderer behaviour.** What the renderer does with `resolved_source` is
  outside this contract.

---

## 10. Stability Statement

This contract is considered stable as of Phase 9 Stage 4.

The inline dict structure (Section 2) and its four fields (`asset_id`,
`resolved_source`, `type`, `version`) must not be changed without a versioned
migration. Specifically:

- No field may be removed.
- No field may be renamed.
- No field's type may be narrowed or widened in a breaking way.
- No new required field may be added without a migration.
- The `type` enum (`icon`, `image`, `logo`) may be extended with new values
  in a backward-compatible way, but existing values must not be removed or
  renamed.

Any change to this contract requires updating this document, incrementing the
schema version in affected YAML artifacts, and providing a migration path for
existing consumers.
