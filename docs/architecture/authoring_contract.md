# pptgen Authoring Contract

Version: 1.0
Owner: Analytics / DevOps Platform Team
Status: Approved

This document is the **canonical authoring contract** for pptgen deck YAML files. It defines the rules that govern how decks must be structured, how slides are ordered, how fields are named, and how placeholders map to template layouts. Both human authors and AI generation systems must conform to this contract.

---

## 1. Deck Metadata Specification

Every deck YAML file must begin with a `deck` block containing these required fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | Yes | Human-readable presentation title |
| `template` | string | Yes | Registered template ID from `templates/registry.yaml` |
| `author` | string | Yes | Name of deck author or authoring team |
| `subtitle` | string | No | Deck subtitle or context line |
| `version` | string | No | Content version — must be a quoted YAML string (e.g. `"1.0"`) |
| `date` | string | No | ISO date string (e.g. `2026-03-22`) |
| `status` | string | No | Lifecycle status: `draft`, `review`, or `final` |
| `description` | string | No | One-line description of deck purpose |
| `tags` | list[string] | No | Classification tags for catalogue and search |

Example:

```yaml
deck:
  title: Weekly Engineering Delivery
  template: ops_review_v1
  author: Platform Engineering
  version: "1.0"
  date: 2026-03-22
  status: draft
  tags:
    - engineering
    - delivery
```

### Constraints
- `title`, `template`, and `author` must not be empty.
- `template` must resolve to an entry in `templates/registry.yaml` with `status: approved`.
- `version` must be a **quoted YAML string**. An unquoted `1.0` is parsed by PyYAML as a float and triggers a coercion warning.

---

## 2. Slides Array

The `slides` key holds an ordered array of slide definitions. It must contain at least one slide.

### Common Optional Fields

Every slide type accepts these optional base fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique slide identifier (used for tracking and references) |
| `notes` | string | Speaker notes — not rendered in the slide body |
| `visible` | boolean | Whether slide renders (default: `true`); set to `false` to skip a slide without deleting it |

### Slide ID Uniqueness

If `id` is present, it must be unique across the entire deck. Duplicates are a hard validation error.

---

## 3. Slide Ordering Rules

Well-structured decks follow a predictable sequence:

1. **Title slide** — always first
2. **Section slide** — opens each logical section of content
3. **Content slides** — bullets, two_column, metric_summary, image_caption
4. Repeat sections 2–3 as needed
5. **Closing metrics or summary slide** — optional, recommended for KPI decks

Slides that violate no ordering rule are still valid. These are guidelines for quality, not hard constraints.

---

## 4. Slide Type Definitions

### 4.1 title

Opens the presentation. Use exactly once as the first slide.

```yaml
- type: title
  title: <string>
  subtitle: <string>
```

Both `title` and `subtitle` are required.

---

### 4.2 section

Section divider. Marks the start of a logical group of slides.

```yaml
- type: section
  section_title: <string>
  section_subtitle: <string>   # optional
```

`section_title` is required. `section_subtitle` is optional.

---

### 4.3 bullets

Standard content slide. Use for lists of points, highlights, decisions, or findings.

```yaml
- type: bullets
  title: <string>
  bullets:
    - <string>
    - <string>
```

`bullets` must contain at least one item. Recommended maximum: **6 bullets per slide**. Exceeding 6 triggers a content quality warning.

---

### 4.4 two_column

Side-by-side comparison slide. Use for current vs. future state, pros vs. cons, or functional splits.

```yaml
- type: two_column
  title: <string>
  left_content:
    - <string>
  right_content:
    - <string>
```

Both `left_content` and `right_content` must contain at least one item.

---

### 4.5 metric_summary

KPI overview slide. Displays up to four metrics in a 2×2 grid.

```yaml
- type: metric_summary
  title: <string>
  metrics:
    - label: <string>
      value: <string>
      unit: <string>   # optional
```

Constraints:
- `metrics` must contain **1 to 4 items**. More than 4 is a hard validation error.
- `value` must be a **quoted YAML string** (e.g. `"99.9"`, not `99.9`).
- `unit` is optional. It is concatenated directly onto `value` with no separator. Authors include any desired spacing in the unit string (e.g. `unit: " ms"` renders as `450 ms`).
- `label` recommended maximum: **40 characters**.
- Composed `value + unit` recommended maximum: **20 characters**.

---

### 4.6 image_caption

Displays a diagram or image with a title and caption.

```yaml
- type: image_caption
  title: <string>
  image_path: <string>
  caption: <string>
```

All three fields are required. `image_path` is a path relative to the working directory when `pptgen build` is executed.

---

## 5. Field Naming Conventions

All YAML keys must use `lowercase_snake_case`.

| Correct | Incorrect |
|---|---|
| `section_title` | `sectionTitle` |
| `left_content` | `leftContent` |
| `image_path` | `imagePath` |
| `metric_summary` | `metricSummary` |

Unknown fields are rejected by the renderer with a `ParseError`. There is no silent pass-through of unrecognised keys.

---

## 6. Formatting Rules

- All required string fields must be non-empty (no `""` or `null`).
- Required arrays must not be empty.
- Boolean `visible` defaults to `true`; only specify it when hiding a slide.
- YAML keys are case-sensitive. `Type: bullets` is not the same as `type: bullets`.
- Do not use YAML anchors or aliases in deck files — they complicate validation and readability.
- Prefer quoted strings for numeric-looking values (especially in `version`, `value`, `date`) to avoid PyYAML type coercion.

---

## 7. Template Placeholder Relationships

Each slide type maps to a named layout in the template `.pptx` file. The renderer finds placeholders by their `UPPERCASE_SNAKE_CASE` shape names.

| Slide Type | Template Layout Name | Placeholders |
|---|---|---|
| `title` | Title Layout | `TITLE`, `SUBTITLE` |
| `section` | Section Layout | `SECTION_TITLE`, `SECTION_SUBTITLE` |
| `bullets` | Bullets Layout | `TITLE`, `BULLETS` |
| `two_column` | Two Column Layout | `TITLE`, `LEFT_CONTENT`, `RIGHT_CONTENT` |
| `metric_summary` | Metric Summary Layout | `TITLE`, `METRIC_1_LABEL`, `METRIC_1_VALUE` … `METRIC_4_LABEL`, `METRIC_4_VALUE` |
| `image_caption` | Image Caption Layout | `TITLE`, `IMAGE`, `CAPTION` |

Templates that omit a required layout or placeholder will cause a `TemplateCompatibilityError` at render time.

---

## 8. Approved Templates

All decks must reference a template registered in `templates/registry.yaml`. Only templates with `status: approved` are recommended for production use.

Current approved templates:

| Template ID | Description |
|---|---|
| `ops_review_v1` | Standard operational review template |

Default template when none is specified: `ops_review_v1`.

---

## 9. Validation Behaviour Summary

| Check | Outcome |
|---|---|
| Missing required deck field | Hard error (ParseError) |
| Unrecognised YAML key | Hard error (ParseError) |
| Unregistered template | Hard error (ValidationResult FAIL) |
| Non-approved template | Warning |
| Unsupported slide `type` | Hard error (ParseError) |
| Duplicate slide `id` | Hard error (ValidationResult FAIL) |
| More than 4 metrics | Hard error (ValidationResult FAIL) |
| More than 6 bullets | Warning |
| Metric `value` not a quoted string | Warning (value still accepted after coercion) |
| `deck.version` not a quoted string | Warning (version still accepted after coercion) |

Errors block rendering. Warnings do not.
