
# Template Placeholder Inventory

This document defines the **official placeholder contract** for the pptgen Phase 1 template layouts.

It documents:
- the layout names
- the placeholders required in each layout
- the purpose of each placeholder

Templates must conform to this specification for the renderer to work correctly.

---

# Template File

Recommended Phase 1 template:

```
templates/ops_review_v1.pptx
```

The template must contain the layouts listed below.

---

# Layout: Title Layout

Purpose: Deck opening slide.

Required placeholders:

| Placeholder | Purpose |
|-------------|---------|
| TITLE | Main presentation title |
| SUBTITLE | Deck subtitle or context |
| AUTHOR | Optional author name |
| DATE | Optional presentation date |

---

# Layout: Section Layout

Purpose: Section divider slide.

Required placeholders:

| Placeholder | Purpose |
|-------------|---------|
| SECTION_TITLE | Title of the section |
| SECTION_SUBTITLE | Optional subtitle or context |

---

# Layout: Bullets Layout

Purpose: Standard content slide.

Required placeholders:

| Placeholder | Purpose |
|-------------|---------|
| TITLE | Slide title |
| BULLETS | Bullet list content |

---

# Layout: Two Column Layout

Purpose: Side-by-side comparison slide.

Required placeholders:

| Placeholder | Purpose |
|-------------|---------|
| TITLE | Slide title |
| LEFT_CONTENT | Left column text |
| RIGHT_CONTENT | Right column text |

---

# Layout: Image Caption Layout

Purpose: Display image or diagram with caption.

Required placeholders:

| Placeholder | Purpose |
|-------------|---------|
| TITLE | Slide title |
| IMAGE | Image placeholder |
| CAPTION | Image caption text |

---

# Layout: Metric Summary Layout

Purpose: Display up to **4 metrics in a 2×2 grid**.

Phase 1 contract: **maximum 4 metrics per slide**.

Required placeholders:

| Placeholder | Purpose |
|-------------|---------|
| TITLE | Slide title |
| METRIC_1_LABEL | Metric 1 label |
| METRIC_1_VALUE | Metric 1 value |
| METRIC_2_LABEL | Metric 2 label |
| METRIC_2_VALUE | Metric 2 value |
| METRIC_3_LABEL | Metric 3 label |
| METRIC_3_VALUE | Metric 3 value |
| METRIC_4_LABEL | Metric 4 label |
| METRIC_4_VALUE | Metric 4 value |

Renderer behavior:

- Metrics populate in order.
- Unused metric placeholders are cleared.
- Units are appended to the value string during rendering.

Example:

```
metrics:
  - label: Uptime
    value: "99.9%"
  - label: Deployments
    value: "324"
```

---

# Placeholder Naming Rules

All placeholders must follow these rules:

- Uppercase
- Snake case
- No spaces
- Deterministic names

Examples:

```
TITLE
SECTION_TITLE
METRIC_1_LABEL
```

Avoid:

```
MetricLabel1
Metric Value
Metric-1
```

---

# Validation Expectations

The template validator should confirm:

1. All required layouts exist.
2. All required placeholders exist in their layouts.
3. Metric Summary layout contains **exactly 9 placeholders**:
   - TITLE
   - 8 metric placeholders.

If any placeholder is missing, rendering should fail with a **TemplateCompatibilityError**.

---

# Phase 1 Template Scope

Phase 1 templates must support:

- title slides
- section slides
- bullet slides
- two-column slides
- image + caption slides
- metric summary slides

Future versions may expand the layout set.

---

# Future Extensions

Possible future extensions:

- metric icons
- metric units placeholder
- 6‑metric grid layouts
- charts
- tables
- agenda slides
- callout slides

These should be introduced in **new template versions** to maintain backward compatibility.

---

# Summary

This placeholder inventory defines the **contract between the pptgen renderer and the PowerPoint template**.

Any template used by pptgen must implement these layouts and placeholder names exactly.

Deviations from this specification may cause rendering failures.
