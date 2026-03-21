
# pptgen Example Decks

This directory contains **ready-to-copy example YAML decks** for the `pptgen` platform.

These examples demonstrate common presentation patterns and serve as a **starting point for creating new decks**.

Most teams will adopt pptgen by **copying and modifying an example** rather than writing YAML from scratch.

---

# Quick Start

The fastest way to create a deck is to copy one of these examples.

Example workflow:

cp examples/executive_update.yaml my_deck.yaml

Edit the file:

deck:
  title: My Project Update
  template: executive_brief_v1
  author: Your Name

Then generate the PowerPoint:

pptgen build --input my_deck.yaml

Output:

my_deck.pptx

---

# Available Examples

| File | Purpose |
|-----|------|
| executive_update.yaml | Executive status updates |
| architecture_overview.yaml | System or platform architecture |
| weekly_ops_report.yaml | Operational reporting |
| product_strategy.yaml | Product or platform strategy |
| kpi_dashboard.yaml | KPI and metrics review |

Each example demonstrates different slide types and deck structures.

---

# Example Slide Types

The examples illustrate the core pptgen slide types.

| Slide Type | Purpose |
|------|------|
| title | Deck title slide |
| section | Logical grouping of slides |
| bullets | Standard content slide |
| two_column | Comparisons or side-by-side ideas |
| metric_summary | KPI or metrics overview |
| image_caption | Diagrams or visual explanations |

---

# Example: Executive Update

This is the most common type of deck used in business reporting.

Typical structure:

Title → Section → Highlights → Section → Priorities → Metrics

Example snippet:

- type: bullets
  title: Key Highlights
  bullets:
    - Platform stability improved
    - Reporting automation reduced manual effort
    - Adoption increased across teams

---

# Example: Architecture Overview

Used for explaining systems, pipelines, or platforms.

Typical structure:

Title → Architecture Summary → Processing Flow → Architecture Diagram

Example snippet:

- type: two_column
  title: Processing Flow
  left_content:
    - YAML definition
    - Schema validation
  right_content:
    - Rendering engine
    - PowerPoint output

---

# Example: KPI Dashboard

Used for metric-driven presentations.

Example:

- type: metric_summary
  title: KPI Snapshot
  metrics:
    - label: Success Rate
      value: "98.4%"
    - label: Monthly Requests
      value: "1.2M"

---

# Using AI to Generate Decks

Many teams generate these YAML decks using AI.

See:

docs/ai-assisted-authoring.md

Typical workflow:

notes → generate_pptgen_deck_yaml → validate_pptgen_deck_yaml → improve_pptgen_deck_yaml → pptgen build

You can also use these examples as **reference prompts for AI**.

---

# Customizing an Example

Common edits include:

Changing the title

deck:
  title: Platform Operations Review

Updating bullets

bullets:
  - Platform stability improved
  - New reporting dashboards launched

Updating metrics

metrics:
  - label: SLA Attainment
    value: "99.7%"

---

# Adding New Examples

If you create a useful deck pattern, consider adding it to this directory.

Example categories that may be useful:

- incident review
- quarterly business review
- product roadmap
- architecture deep dive
- operational KPI dashboards

Each example should:

- use supported slide types
- pass schema validation
- follow the template authoring standard
- be simple enough for new users to understand

---

# Related Documentation

| Document | Purpose |
|------|------|
| Deck Authoring Guide | How to write YAML decks manually |
| AI-Assisted Deck Authoring | Using Claude to generate decks |
| Template Authoring Standard | Rules for creating templates |
| Deck YAML Schema Specification | Formal deck structure |

---

# Summary

The examples in this directory provide **working starting points for pptgen decks**.

Most teams follow this workflow:

copy example → modify YAML → build deck

This approach allows teams to move quickly from **idea → structured content → PowerPoint presentation**.
