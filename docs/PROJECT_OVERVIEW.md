
# pptgen Platform Overview

Version: 1.0  
Owner: Analytics / DevOps Platform Team  

---

# Purpose

`pptgen` is a template-driven presentation generation platform that converts structured YAML into PowerPoint presentations.

The platform enables teams to:

- generate consistent presentations
- reduce manual slide formatting
- automate reporting and updates
- use AI-assisted workflows for deck creation

Instead of manually designing slides in PowerPoint, users define presentation content using structured YAML, which is then rendered into a formatted deck using predefined templates.

---

# Platform Philosophy

The pptgen platform is built on three core principles.

## Separation of Concerns

| Layer | Responsibility |
|------|----------------|
| Content | YAML deck definition |
| Layout | PowerPoint templates |
| Rendering | pptgen engine |

This separation allows content to change without modifying templates or rendering logic.

## Repeatability

Decks can be regenerated consistently from the same YAML definition.

Use cases include:

- weekly operational reports
- monthly KPI dashboards
- executive updates
- architecture documentation

## AI-Assisted Authoring

pptgen integrates with AI workflows using Claude Code skills.

AI can:

- generate deck YAML
- validate structure
- improve slide quality

This allows teams to move quickly from **notes → structured presentation → PowerPoint**.

---

# High-Level Architecture

ideas / notes  
↓  
YAML deck definition  
↓  
schema validation  
↓  
template lookup  
↓  
pptgen rendering engine  
↓  
PowerPoint output (.pptx)

---

# Core Components

## Deck YAML

Deck content is defined using YAML.

Example:

```yaml
deck:
  title: DevOps Strategy
  template: ops_review_v1
  author: David Harris

slides:
  - type: title
    title: DevOps Strategy
```

## Templates

Templates are PowerPoint layouts that define how slides should look.

Templates control:

- typography
- layout
- branding
- slide positioning

## Rendering Engine

The `pptgen` engine converts YAML into PowerPoint slides.

Example command:

```
pptgen build --input deck.yaml
```

Output:

```
deck.pptx
```

---

# AI-Assisted Workflow

notes  
↓  
generate_pptgen_deck_yaml  
↓  
validate_pptgen_deck_yaml  
↓  
improve_pptgen_deck_yaml  
↓  
validate_pptgen_deck_yaml  
↓  
pptgen build  

---

# Repository Structure

```
pptgen/
│
├─ docs/
│  ├─ PROJECT_OVERVIEW.md
│  ├─ deck-authoring-guide.md
│  ├─ ai-assisted-authoring.md
│  ├─ template-authoring-standard.md
│  ├─ template-validation-checklist.md
│  └─ deck-yaml-schema-specification.md
│
├─ skills/
│  ├─ README.md
│  ├─ generate_pptgen_deck_yaml.md
│  ├─ validate_pptgen_deck_yaml.md
│  └─ improve_pptgen_deck_yaml.md
│
├─ examples/
│  ├─ README.md
│  ├─ executive_update.yaml
│  ├─ architecture_overview.yaml
│  ├─ weekly_ops_report.yaml
│  ├─ product_strategy.yaml
│  └─ kpi_dashboard.yaml
│
├─ templates/
│
└─ pptgen/
```

---

# Documentation Map

| Document | Purpose |
|--------|--------|
| PROJECT_OVERVIEW.md | Platform architecture overview |
| Deck Authoring Guide | Manual YAML deck creation |
| AI-Assisted Authoring Guide | Claude workflow |
| Template Authoring Standard | Rules for template creation |
| Template Validation Checklist | Template quality validation |
| Deck YAML Schema Specification | Formal YAML structure |

---

# Common Workflows

## Manual Deck Creation

create YAML deck  
↓  
validate YAML  
↓  
pptgen build  

## AI-Assisted Deck Creation

notes  
↓  
generate deck YAML  
↓  
validate structure  
↓  
improve slide quality  
↓  
render PowerPoint  

---

# Use Cases

| Use Case | Description |
|--------|--------|
| Executive updates | Leadership reporting |
| Architecture reviews | System documentation |
| KPI dashboards | Metrics and reporting |
| Operational reports | Weekly or monthly updates |
| Strategy decks | Product or platform plans |

---

# Benefits

## Consistency
All decks follow standardized templates.

## Speed
Presentations can be generated in minutes.

## Automation
Reports can be regenerated automatically.

## AI Integration
AI can assist with content creation while maintaining structure.

---

# Summary

pptgen transforms presentation creation from a manual design process into a structured content pipeline.

The platform combines:

- YAML-based deck definitions
- reusable PowerPoint templates
- deterministic rendering
- AI-assisted authoring

This enables teams to move from **ideas → structured content → presentation-ready slides** quickly and consistently.
