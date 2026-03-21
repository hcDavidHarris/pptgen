
# Deck Authoring Guide

Version: 1.2

## Overview

pptgen decks are defined using structured YAML.  
The YAML describes **content and structure**, while templates control **visual layout**.

Typical workflow:

ideas → YAML → pptgen build → PowerPoint

Teams can author YAML manually or generate it using AI tools such as ChatGPT or M365 Copilot.

---

## Basic Deck Structure

```yaml
deck:
  title: Example Presentation
  template: executive_brief_v1
  author: Your Name

slides:
  - type: title
    title: Example Presentation
    subtitle: Project Update
```

Required fields:

| Field | Description |
|------|-------------|
| title | Presentation title |
| template | Template name |
| author | Deck author |

---

## Supported Slide Types

| Slide Type | Purpose |
|------------|--------|
| title | Opening slide |
| section | Section divider |
| bullets | Standard content slide |
| two_column | Side-by-side comparison |
| metric_summary | KPI overview |
| image_caption | Image with caption |

---

## Example Bullet Slide

```yaml
- type: bullets
  title: Key Highlights
  bullets:
    - Platform stability improved
    - Reporting automation reduced manual effort
    - Adoption increased across teams
```

Guidelines:

• Keep bullets concise  
• Prefer 3–6 bullets per slide  
• Focus each slide on one idea

---

## Example Metric Slide

```yaml
- type: metric_summary
  title: KPI Snapshot
  metrics:
    - label: Success Rate
      value: "98.4%"
    - label: Monthly Requests
      value: "1.2M"
```

Use metric slides when presenting numerical summaries.

---

## Using AI to Generate Deck YAML

Teams may generate YAML automatically using AI.

Example prompt:

"Create a pptgen YAML deck for a DevOps strategy presentation with sections for Challenges, Improvements, and KPIs."

AI workflow:

notes → generate YAML → validate → improve → pptgen build

See:

docs/ai-assisted-authoring.md

---

## Building the Deck

Run:

```
pptgen build --input deck.yaml
```

Output:

```
deck.pptx
```

---

## Best Practices

• Start with an example deck from `examples/`  
• Keep slide titles concise  
• Avoid overcrowded slides  
• Validate YAML before building  
• Use templates consistently

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| AI‑Assisted Deck Authoring | Using Claude skills |
| Template Authoring Standard | Template rules |
| Deck YAML Schema Specification | YAML contract |
