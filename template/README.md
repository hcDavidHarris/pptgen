
# pptgen Template System

This directory contains **PowerPoint templates used by the pptgen rendering engine**.

Templates define the **visual layout and branding** of generated presentations, while YAML files define the **content**.

The pptgen platform separates:

| Layer | Responsibility |
|------|----------------|
| YAML Deck | Presentation content |
| Template | Slide layout and visual style |
| Renderer | Converts YAML into PowerPoint |

This separation allows teams to change **presentation content without modifying templates**.

---

# How Templates Work

Each YAML slide references a **slide type**.

Example YAML:

```yaml
- type: bullets
  title: Key Highlights
  bullets:
    - Platform stability improved
    - Reporting automation reduced manual effort
```

The pptgen renderer looks for the **matching layout inside the template**.

Example mapping:

| YAML Slide Type | Template Layout |
|-----------------|----------------|
| title | Title Slide |
| section | Section Header |
| bullets | Title and Content |
| two_column | Two Content |
| metric_summary | Metrics Layout |
| image_caption | Picture with Caption |

Templates must contain layouts compatible with these slide types.

---

# Supported Slide Types

All templates must support the following slide types.

| Slide Type | Purpose |
|------------|---------|
| `title` | Deck title slide |
| `section` | Section header slide |
| `bullets` | Standard bullet slide |
| `two_column` | Side-by-side comparison |
| `metric_summary` | KPI summary slide |
| `image_caption` | Image with caption |

If a template does not include a required layout, pptgen may fail during rendering.

---

# Template Naming Convention

Templates should follow a consistent naming convention.

Example:

executive_brief_v1.pptx  
ops_review_v1.pptx  
architecture_overview_v1.pptx

Naming pattern:

<template_category>_<version>.pptx

Versioning allows template changes without breaking existing decks.

---

# Recommended Template Layouts

## Title Slide

Expected placeholders:

- title
- subtitle

## Section Slide

Expected placeholders:

- section_title
- optional subtitle

## Bullet Slide

Expected placeholders:

- title
- content placeholder (for bullets)

## Two Column Slide

Expected placeholders:

- title
- left content
- right content

## Metric Summary Slide

Expected placeholders:

- title
- metric fields

## Image Caption Slide

Expected placeholders:

- title
- image placeholder
- caption

---

# Placeholder Best Practices

- Keep layouts simple
- Use standard PowerPoint placeholder types (Title, Content, Picture)
- Avoid hardcoded content
- Maintain consistent layouts across templates

---

# Template Development Workflow

1. Create PowerPoint layout
2. Add required placeholders
3. Test using an example YAML deck
4. Validate slide rendering
5. Version the template

Example test command:

pptgen build --input examples/executive_update.yaml

---

# Template Versioning

Example:

executive_brief_v1.pptx  
executive_brief_v2.pptx

Deck YAML should reference a specific version:

```yaml
deck:
  template: executive_brief_v1
```

---

# Adding New Templates

When adding a new template:

1. Place the `.pptx` file in this directory
2. Follow naming conventions
3. Ensure all slide types are supported
4. Test using example decks

---

# Related Documentation

| Document | Purpose |
|----------|---------|
| Deck Authoring Guide | How to write YAML decks |
| AI-Assisted Authoring Guide | AI deck creation workflow |
| Template Authoring Standard | Detailed template rules |
| Template Validation Checklist | Template quality validation |
| Deck YAML Schema Specification | YAML content structure |

---

# Summary

Templates define the **visual structure of pptgen-generated presentations**.

By separating **content (YAML)** from **layout (templates)**, pptgen enables:

- consistent branding
- automated slide generation
- repeatable presentation workflows
- AI-assisted content creation
