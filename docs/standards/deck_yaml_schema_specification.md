# Deck YAML Schema Specification

### pptgen Content Definition Standard

Version: 1.0\
Owner: Analytics / DevOps Platform Team\
Status: Draft Standard

------------------------------------------------------------------------

# 1. Purpose

This document defines the **standard YAML schema for deck definition
files** used by the `pptgen` platform.

The purpose of this schema is to ensure that:

-   deck files are structured consistently across teams
-   slide content can be validated before rendering
-   the rendering engine can process decks reliably
-   content definitions remain maintainable as the platform evolves

All YAML deck files submitted for use with `pptgen` **must conform to
this specification**.

------------------------------------------------------------------------

# 2. Scope

This specification governs:

-   deck-level metadata
-   slide definitions
-   slide-specific fields
-   optional content sections
-   validation expectations

Related documents:

-   Template rules → `docs/template-authoring-standard.md`
-   Template validation → `docs/template-validation-checklist.md`

------------------------------------------------------------------------

# 3. Design Principles

Deck YAML files must follow these principles.

## Structured, Not Freeform

Deck content must follow a defined schema. Arbitrary keys are not
allowed.

## Human Readable

Deck YAML should be easy for analysts and engineers to read and edit.

## Deterministic

The same YAML input must always produce the same slide structure.

## Template Aware

Decks must reference approved templates and supported slide types.

## Validatable

All required fields must be explicitly defined so validation can occur
before rendering.

------------------------------------------------------------------------

# 4. Top‑Level Document Structure

Each deck YAML file must contain the following top‑level sections.

``` yaml
deck:
slides:
```

  Field    Type     Required   Description
  -------- -------- ---------- --------------------
  deck     object   Yes        Deck metadata
  slides   array    Yes        Ordered slide list

------------------------------------------------------------------------

# 5. Deck Metadata Schema

## Required Fields

  Field      Type     Description
  ---------- -------- ---------------------------
  title      string   Human readable deck title
  template   string   Registered template ID
  author     string   Deck author

## Optional Fields

  Field         Type              Description
  ------------- ----------------- ----------------------
  subtitle      string            Deck subtitle
  version       string            Content version
  date          string            ISO date recommended
  status        string            draft, review, final
  description   string            Deck description
  tags          array\[string\]   Classification tags

Example:

``` yaml
deck:
  title: DevOps Strategy
  subtitle: 30-60-90 Day Plan
  template: ops_review_v1
  author: David Harris
  version: 1.0
  date: 2026-03-21
  status: draft
  tags:
    - devops
    - strategy
```

------------------------------------------------------------------------

# 6. Slides Array

The `slides` array defines the ordered slides in the presentation.

Each slide must contain a supported `type`.

Common optional fields:

  Field     Type      Description
  --------- --------- --------------------------------------
  id        string    Unique slide identifier
  notes     string    Speaker notes
  visible   boolean   Whether slide renders (default true)

------------------------------------------------------------------------

# 7. Supported Slide Types

    title
    section
    bullets
    two_column
    metric_summary
    image_caption

------------------------------------------------------------------------

# 8. Slide Definitions

## Title Slide

Required fields:

``` yaml
type: title
title: string
subtitle: string
```

Example:

``` yaml
- type: title
  title: DevOps Transformation
  subtitle: 30‑60‑90 Day Plan
```

------------------------------------------------------------------------

## Section Slide

Required fields:

``` yaml
type: section
section_title: string
```

Optional:

    section_subtitle

------------------------------------------------------------------------

## Bullet Slide

Required fields:

``` yaml
type: bullets
title: string
bullets: array[string]
```

Example:

``` yaml
- type: bullets
  title: Strategic Priorities
  bullets:
    - Stabilize production pipelines
    - Improve deployment consistency
```

Rules:

-   bullets must contain at least one item

------------------------------------------------------------------------

## Two Column Slide

Required fields:

``` yaml
type: two_column
title: string
left_content: array[string]
right_content: array[string]
```

------------------------------------------------------------------------

## Metric Summary Slide

Required fields:

``` yaml
type: metric_summary
title: string
metrics: array[object]
```

Constraints:

-   `metrics` array must contain **1 to 4 items**
-   Arrays with 0 items or more than 4 items are validation errors

Metric object schema:

  Field   Type     Required   Description
  ------- -------- ---------- --------------------------------------------------
  label   string   Yes        Metric name. Recommended maximum 40 characters.
  value   string   Yes        Metric value. Must be a quoted YAML string.
  unit    string   No         Optional unit. Concatenated directly onto value.

Unit rendering rule:

When `unit` is present, the renderer concatenates `value` and `unit` directly
with no separator. The author controls spacing by including it in the unit string.

Examples:

  YAML value   YAML unit   Rendered text
  ------------ ----------- --------------
  "99.9"       "%"         99.9%
  "450"        " ms"       450 ms
  "1.2M"       (absent)    1.2M

`value` must always be authored as a quoted YAML string. The renderer treats
it as opaque display text and does not parse it numerically.

Example:

``` yaml
- type: metric_summary
  title: KPI Snapshot
  metrics:
    - label: Success Rate
      value: "99.9"
      unit: "%"
    - label: Monthly Requests
      value: "1.2M"
    - label: Delivery Reliability
      value: "99.2%"
```

------------------------------------------------------------------------

## Image Caption Slide

Required fields:

``` yaml
type: image_caption
title: string
image_path: string
caption: string
```

Example:

``` yaml
- type: image_caption
  title: Platform Architecture
  image_path: assets/architecture.png
  caption: pptgen system architecture overview
```

------------------------------------------------------------------------

# 9. General Validation Rules

Deck rules:

-   `deck.title` must not be empty
-   `deck.template` must reference a registered template
-   slides array must contain at least one slide

Slide rules:

-   every slide must define `type`
-   slide type must be supported by template
-   unknown fields are not allowed
-   slide `id` values must be unique if present

Content rules:

-   required arrays must not be empty
-   strings must not be null

------------------------------------------------------------------------

# 10. Field Naming Convention

All YAML keys must use:

    lowercase_snake_case

Examples:

    section_title
    left_content
    image_path

Avoid:

    sectionTitle
    leftContent

------------------------------------------------------------------------

# 11. Example Full Deck

``` yaml
deck:
  title: DevOps Strategy
  template: ops_review_v1
  author: David Harris

slides:
  - type: title
    title: DevOps Transformation
    subtitle: 30‑60‑90 Day Plan

  - type: bullets
    title: Strategic Priorities
    bullets:
      - Stabilize pipelines
      - Improve observability

  - type: metric_summary
    title: KPI Snapshot
    metrics:
      - label: Success Rate
        value: "98%"
      - label: Monthly Requests
        value: "1.2M"
```

------------------------------------------------------------------------

# 12. Invalid Examples

Invalid field:

``` yaml
bullet_list:
```

Reason: must use `bullets`.

Invalid naming:

``` yaml
leftContent:
```

Reason: must use `lowercase_snake_case`.

Invalid array:

``` yaml
bullets: []
```

Reason: must contain at least one bullet.

------------------------------------------------------------------------

# 13. Deck Authoring Workflow

Recommended workflow:

1.  Select an approved template
2.  Create deck YAML
3.  Add slides using supported types
4.  Run validation
5.  Build presentation

Example validation:

    pptgen validate --input deck.yaml

------------------------------------------------------------------------

# 14. Versioning

Schema updates follow semantic rules:

-   backward compatible additions allowed
-   breaking changes require new schema version

Example compatibility:

  Schema   Renderer
  -------- ----------
  1.0      1.0+

------------------------------------------------------------------------

# 15. Common Authoring Errors

Most frequent issues:

-   unsupported fields
-   wrong naming style
-   missing required fields
-   empty bullet arrays
-   unsupported slide type

------------------------------------------------------------------------

# 16. Future Enhancements

Potential additions:

-   nested bullets
-   chart slides
-   table slides
-   speaker notes
-   conditional slides

------------------------------------------------------------------------

# Final Note

This specification defines the **content contract for pptgen deck
files**.

Following the schema ensures decks are:

-   consistent
-   validatable
-   template compatible
-   reliable to render
