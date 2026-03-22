# Slide Type Reference

Version: 1.0
Owner: Analytics / DevOps Platform Team

This is the authoritative per-type reference for all supported pptgen slide types. For each type it defines: purpose, required fields, optional fields, a YAML example, content guidelines, and compatible templates.

---

## title

**Purpose:** Opens the presentation. Should always be the first slide.

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `type` | literal `"title"` | Identifies the slide type |
| `title` | string | Main presentation title |
| `subtitle` | string | Subtitle or context line |

**Optional fields:** `id`, `notes`, `visible`

**YAML example:**

```yaml
- type: title
  id: title_slide
  title: DevOps Transformation
  subtitle: 30-60-90 Day Platform Plan
```

**Guidelines:**
- Use exactly once per deck, as the first slide.
- Keep `title` under 60 characters.
- `subtitle` can include dates, team name, or sprint context.

**Template layout:** `Title Layout`
**Placeholders:** `TITLE`, `SUBTITLE`

---

## section

**Purpose:** Section divider slide. Marks the start of a logical group of content slides.

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `type` | literal `"section"` | Identifies the slide type |
| `section_title` | string | Section heading |

**Optional fields:** `section_subtitle`, `id`, `notes`, `visible`

**YAML example:**

```yaml
- type: section
  id: challenges_section
  section_title: Current Challenges
  section_subtitle: Q1 2026 Assessment
```

**Guidelines:**
- Place before groups of 2 or more thematically related content slides.
- Keep `section_title` under 50 characters.
- `section_subtitle` is useful for dates, quarters, or scope context.

**Template layout:** `Section Layout`
**Placeholders:** `SECTION_TITLE`, `SECTION_SUBTITLE`

---

## bullets

**Purpose:** Standard content slide. Use for lists, highlights, decisions, findings, or summaries.

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `type` | literal `"bullets"` | Identifies the slide type |
| `title` | string | Slide title |
| `bullets` | list[string] | Bullet point items (non-empty) |

**Optional fields:** `id`, `notes`, `visible`

**YAML example:**

```yaml
- type: bullets
  id: weekly_highlights
  title: Weekly Highlights
  bullets:
    - Renderer stabilized for metric slides
    - Example library expanded with 12 new patterns
    - Validation now catches coercion warnings
    - CLI scaffold command implemented
```

**Guidelines:**
- `bullets` must contain at least one item.
- Recommended: **3–6 bullets per slide**. More than 6 triggers a quality warning.
- Write bullets as short phrases, not full sentences.
- If you have more than 6 items, split into two slides under the same section.
- Keep each bullet under 80 characters.

**Template layout:** `Bullets Layout`
**Placeholders:** `TITLE`, `BULLETS`

---

## two_column

**Purpose:** Side-by-side comparison slide. Use for current vs. future state, pros vs. cons, functional splits, or parallel lists.

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `type` | literal `"two_column"` | Identifies the slide type |
| `title` | string | Slide title |
| `left_content` | list[string] | Left column items (non-empty) |
| `right_content` | list[string] | Right column items (non-empty) |

**Optional fields:** `id`, `notes`, `visible`

**YAML example:**

```yaml
- type: two_column
  id: functional_rocks
  title: Functional Priorities
  left_content:
    - Product: define roadmap and adoption targets
    - Engineering: implement rendering MVP
    - Operations: establish template management process
  right_content:
    - Analytics: create example deck library
    - Leadership: align EOS reporting cadence
    - Enablement: publish onboarding guides
```

**Guidelines:**
- Keep column lengths balanced where possible.
- Label items with a prefix (e.g. `Engineering:`) when items from different domains share a slide.
- Avoid more than 6 items per column.
- Works well as a "before vs. after" or "us vs. them" structure.

**Template layout:** `Two Column Layout`
**Placeholders:** `TITLE`, `LEFT_CONTENT`, `RIGHT_CONTENT`

---

## metric_summary

**Purpose:** KPI overview slide. Displays up to four metrics in a 2×2 grid layout.

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `type` | literal `"metric_summary"` | Identifies the slide type |
| `title` | string | Slide title |
| `metrics` | list[MetricItem] | 1–4 metric definitions |

**MetricItem fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Metric name (max 40 characters) |
| `value` | string | Yes | Metric value — always quoted (e.g. `"99.9"`) |
| `unit` | string | No | Unit string, concatenated directly onto value |

**Optional slide fields:** `id`, `notes`, `visible`

**YAML example:**

```yaml
- type: metric_summary
  id: dora_metrics
  title: DORA Metrics
  metrics:
    - label: Deployment Frequency
      value: "24/day"
    - label: Lead Time for Changes
      value: "42"
      unit: " min"
    - label: Change Failure Rate
      value: "3%"
    - label: MTTR
      value: "17"
      unit: " min"
```

**Unit rendering:**

| value | unit | Renders as |
|---|---|---|
| `"99.9"` | `"%"` | `99.9%` |
| `"450"` | `" ms"` | `450 ms` |
| `"24/day"` | absent | `24/day` |

**Guidelines:**
- Maximum **4 metrics** per slide. Exceeding 4 is a hard validation error.
- `value` must always be a **quoted YAML string**. Unquoted numbers trigger a coercion warning.
- If you have more than 4 metrics, use two separate metric slides under the same section.
- A slide with a single metric triggers a quality warning — consider using a `bullets` slide instead.

**Template layout:** `Metric Summary Layout`
**Placeholders:** `TITLE`, `METRIC_1_LABEL`, `METRIC_1_VALUE`, `METRIC_2_LABEL`, `METRIC_2_VALUE`, `METRIC_3_LABEL`, `METRIC_3_VALUE`, `METRIC_4_LABEL`, `METRIC_4_VALUE`

---

## image_caption

**Purpose:** Displays a diagram, screenshot, or architecture diagram with a title and caption.

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `type` | literal `"image_caption"` | Identifies the slide type |
| `title` | string | Slide title |
| `image_path` | string | Path to image file relative to working directory |
| `caption` | string | Caption text displayed below the image |

**Optional fields:** `id`, `notes`, `visible`

**YAML example:**

```yaml
- type: image_caption
  id: architecture_diagram
  title: Platform Architecture Overview
  image_path: assets/platform_architecture.png
  caption: pptgen three-layer architecture — content, layout, and rendering
```

**Guidelines:**
- `image_path` is relative to the working directory when `pptgen build` is run.
- Use for system diagrams, architecture drawings, process flows, or screenshots.
- Keep `caption` descriptive but concise (one sentence).
- Supported image formats depend on the python-pptx library (PNG and JPEG are standard).

**Template layout:** `Image Caption Layout`
**Placeholders:** `TITLE`, `IMAGE`, `CAPTION`

---

## Compatibility Matrix

| Slide Type | ops_review_v1 |
|---|---|
| `title` | Supported |
| `section` | Supported |
| `bullets` | Supported |
| `two_column` | Supported |
| `metric_summary` | Supported |
| `image_caption` | Supported |

All Phase 1 slide types are supported by `ops_review_v1`.

---

## Summary Table

| Type | Use For | Max Items | Hard Limit |
|---|---|---|---|
| `title` | Opening slide | 1 per deck | — |
| `section` | Section dividers | Unlimited | — |
| `bullets` | Lists and highlights | Recommend ≤6 | none |
| `two_column` | Comparisons | Recommend ≤6 per column | none |
| `metric_summary` | KPIs and metrics | Max 4 metrics | 4 (error) |
| `image_caption` | Diagrams and visuals | 1 image per slide | — |
