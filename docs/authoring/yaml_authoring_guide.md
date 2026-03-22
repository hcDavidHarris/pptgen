# YAML Authoring Guide

Version: 1.0
Owner: Analytics / DevOps Platform Team

This guide walks through how to write a valid pptgen YAML deck file from scratch. It covers structure, formatting rules, metric patterns, title guidance, and composition patterns for common presentation types.

---

## 1. Deck YAML Anatomy

A pptgen deck file has exactly two top-level keys: `deck` and `slides`.

```yaml
deck:
  title: <required>
  template: <required>
  author: <required>

slides:
  - type: <required>
    ...
```

Nothing else belongs at the top level. Any additional key (e.g. `metadata:`, `config:`) is a parse error.

---

## 2. Complete Example Deck

```yaml
deck:
  title: Weekly Engineering Delivery Update
  template: ops_review_v1
  author: Platform Engineering
  version: "1.0"
  date: 2026-03-22
  status: draft

slides:
  - type: title
    id: title_slide
    title: Weekly Engineering Delivery Update
    subtitle: Platform Team — Sprint 24

  - type: section
    id: highlights_section
    section_title: Weekly Highlights

  - type: bullets
    id: highlights
    title: This Week's Highlights
    bullets:
      - Renderer stabilized for metric and two-column slides
      - Example library expanded with 12 new patterns
      - Validation now catches coercion warnings

  - type: section
    id: blockers_section
    section_title: Risks and Blockers

  - type: bullets
    id: blockers
    title: Active Blockers
    bullets:
      - Template dependency still requires manual setup
      - CLI workspace init not yet implemented

  - type: metric_summary
    id: kpis
    title: Delivery Metrics
    metrics:
      - label: Features Completed
        value: "4"
      - label: Active Stories
        value: "18"
      - label: Blocked Items
        value: "2"
      - label: Weekly Completion Rate
        value: "82%"
```

---

## 3. Formatting Rules

### Keys

All YAML keys use `lowercase_snake_case`.

```yaml
# Correct
section_title: Current State
left_content:
  - Item one

# Wrong — will be rejected
sectionTitle: Current State
leftContent:
  - Item one
```

### Strings

Quote strings that contain colons, special characters, or look like numbers:

```yaml
# These must be quoted
version: "1.0"        # unquoted 1.0 becomes a float
value: "99.9"         # unquoted 99.9 becomes a float
date: "2026-03-22"    # recommended but not strictly required
title: "Step 1: Plan" # colon in value requires quotes
```

### Arrays

Required arrays must not be empty:

```yaml
# Wrong — parse error
bullets: []

# Correct
bullets:
  - At least one item
```

### Boolean

Use bare `true` / `false` for the `visible` field:

```yaml
visible: false   # hides slide without deleting it
```

---

## 4. Metric Formatting

The `metric_summary` slide follows a strict contract.

### Basic pattern

```yaml
- type: metric_summary
  title: KPI Snapshot
  metrics:
    - label: Deployment Frequency
      value: "24/day"
    - label: Change Failure Rate
      value: "3%"
    - label: Lead Time for Changes
      value: "42"
      unit: " min"
    - label: MTTR
      value: "17"
      unit: " min"
```

### Rules

- `value` must always be a **quoted string**.
- `unit` is concatenated directly onto `value` with no separator. Add a leading space if needed.
- Maximum **4 metrics** per slide.
- `label` should be 40 characters or fewer.
- Composed `value + unit` should be 20 characters or fewer.

### Unit examples

| label | value | unit | Renders as |
|---|---|---|---|
| Success Rate | `"99.9"` | `"%"` | `99.9%` |
| Response Time | `"450"` | `" ms"` | `450 ms` |
| Monthly Volume | `"1.2M"` | absent | `1.2M` |

---

## 5. Title Length Guidance

Short titles make better slides. The template has limited space.

| Element | Recommended max |
|---|---|
| Slide `title` | 60 characters |
| `section_title` | 50 characters |
| `subtitle` | 80 characters |
| Bullet item | 80 characters |
| Metric `label` | 40 characters |
| Metric `value + unit` | 20 characters |

These are not hard errors — they are layout quality guidelines.

---

## 6. Slide Composition Patterns

### Pattern: Status Update

Use for weekly or sprint-based reporting.

```
title → section (Highlights) → bullets → section (Blockers) → bullets → metric_summary
```

### Pattern: Strategy Deck

Use for product or platform strategy presentations.

```
title → section → bullets → section → bullets → two_column → metric_summary
```

### Pattern: Architecture Review

Use for system design or ADR presentations.

```
title → section → bullets → image_caption → section → bullets → two_column
```

### Pattern: Executive KPI Summary

Use for leadership dashboards.

```
title → metric_summary → section → bullets → metric_summary
```

---

## 7. Using the `id` Field

The `id` field is optional but recommended for non-trivial decks. It makes slides easier to reference in reviews, playbooks, and AI-assisted edits.

```yaml
- type: bullets
  id: weekly_highlights
  title: Weekly Highlights
  bullets:
    - ...
```

IDs must be unique across the entire deck. Use `lowercase_snake_case`.

---

## 8. Using the `visible` Field

Setting `visible: false` skips a slide during rendering without removing it from the YAML. Useful for work-in-progress slides or conditional content.

```yaml
- type: bullets
  id: future_roadmap
  visible: false
  title: Future Roadmap (Draft)
  bullets:
    - Item not ready for this review
```

---

## 9. Building and Validating

```bash
# Validate without rendering
pptgen validate --input deck.yaml

# Build the presentation
pptgen build --input deck.yaml

# Specify output location
pptgen build --input deck.yaml --output output/my_deck.pptx
```

Always validate before building. Validation catches structural errors and quality warnings before any file is written.

---

## 10. Related Documentation

| Document | Purpose |
|---|---|
| [authoring_contract.md](../architecture/authoring_contract.md) | Canonical schema and field rules |
| [slide_type_reference.md](slide_type_reference.md) | Per-type field reference |
| [ai_generation_rules.md](ai_generation_rules.md) | Rules for AI-generated decks |
| [deck_yaml_schema_specification.md](../standards/deck_yaml_schema_specification.md) | Formal schema specification |
