
# AI-Assisted Deck Authoring Guide
### Using Claude Code with pptgen

Version: 1.0  
Owner: Analytics / DevOps Platform Team  

---

# Overview

The `pptgen` platform supports **AI-assisted deck authoring** using Claude Code skills.

Instead of manually writing YAML, AI can:

- generate deck YAML from notes
- validate YAML against platform rules
- improve slide quality and deck structure

This allows teams to move quickly from **ideas → presentation** while still enforcing standardized templates.

---

# AI-Assisted Workflow

The recommended workflow combines three Claude skills with the `pptgen` rendering engine.

```
notes or outline
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
        ↓
PowerPoint deck
```

Each skill performs a specific role in the pipeline.

---

# The Three Core Claude Skills

The pptgen AI workflow uses three complementary skills.

| Skill | Purpose |
|------|--------|
| `generate_pptgen_deck_yaml` | Create deck YAML from notes or outlines |
| `validate_pptgen_deck_yaml` | Verify schema compliance and detect errors |
| `improve_pptgen_deck_yaml` | Improve slide quality and presentation structure |

These skills allow Claude to act as a **presentation assistant**, not just a text generator.

---

# Skill 1 — Generate Deck YAML

### Skill

```
generate_pptgen_deck_yaml
```

### Purpose

Create a valid pptgen YAML deck from:

- meeting notes
- strategy outlines
- architecture descriptions
- KPI summaries
- bullet point lists

### Example Prompt

```
Use the generate_pptgen_deck_yaml skill.

Create a pptgen deck for a DevOps strategy presentation.

Sections:
- Current Challenges
- Platform Improvements
- KPI Snapshot

Challenges:
- fragmented pipelines
- poor observability

Improvements:
- standardized deployment
- centralized monitoring

Metrics:
- success rate 98%
- monthly requests 1.2M
```

### Example Output

```yaml
deck:
  title: DevOps Strategy
  template: ops_review_v1
  author: David Harris

slides:
  - type: title
    title: DevOps Strategy
    subtitle: Platform Improvement Plan

  - type: section
    section_title: Current Challenges

  - type: bullets
    title: Operational Challenges
    bullets:
      - Fragmented pipelines
      - Limited observability

  - type: section
    section_title: Platform Improvements

  - type: bullets
    title: Proposed Improvements
    bullets:
      - Standardized deployment pipelines
      - Centralized monitoring

  - type: metric_summary
    title: KPI Snapshot
    metrics:
      - label: Success Rate
        value: "98%"
      - label: Monthly Requests
        value: "1.2M"
```

---

# Skill 2 — Validate Deck YAML

### Skill

```
validate_pptgen_deck_yaml
```

### Purpose

Verify that the YAML deck:

- follows the pptgen schema
- uses supported slide types
- includes required fields
- contains valid content structures

### Example Prompt

```
Use validate_pptgen_deck_yaml to validate this deck.
```

### Example Output

```
Validation Result: PASS

Schema Validation
✔ deck.title present
✔ deck.template present
✔ deck.author present
✔ slides array valid

Slide Validation
✔ slide types supported
✔ bullet slides contain items
✔ metric summary slides valid

Warnings
None
```

### Example Failure

```
Validation Result: FAIL

Errors
✖ missing deck.template
✖ unsupported slide type "bullet_list"

Warnings
⚠ slide contains 8 bullets
```

The validator helps catch issues **before running `pptgen build`**.

---

# Skill 3 — Improve Deck YAML

### Skill

```
improve_pptgen_deck_yaml
```

### Purpose

Refine a draft deck to make it more presentation-friendly.

Typical improvements include:

- simplifying long bullet text
- splitting overcrowded slides
- improving slide titles
- reorganizing slide flow
- converting bullets into better slide types

### Example Prompt

```
Use improve_pptgen_deck_yaml to improve this deck for an executive audience.
```

### Typical Improvements

Before:

```yaml
- type: bullets
  title: Detailed Overview of Challenges We Are Currently Facing
  bullets:
    - Our deployment processes vary widely across teams
    - Observability tools are not standardized
    - Ownership boundaries are unclear
    - Pipelines evolved organically without governance
```

After:

```yaml
- type: section
  section_title: Current Challenges

- type: bullets
  title: Platform Operations Challenges
  bullets:
    - Fragmented deployment practices
    - Inconsistent observability tooling
    - Unclear ownership boundaries
```

---

# Example End-to-End Workflow

Example AI-assisted session.

### Step 1 — Generate YAML

```
generate_pptgen_deck_yaml from these notes
```

### Step 2 — Validate YAML

```
validate_pptgen_deck_yaml
```

### Step 3 — Improve Deck

```
improve_pptgen_deck_yaml
```

### Step 4 — Validate Again

```
validate_pptgen_deck_yaml
```

### Step 5 — Build Deck

```
pptgen build --input deck.yaml
```

Output:

```
deck.pptx
```

---

# Recommended Prompt Patterns

### Strategy Deck

```
Generate a pptgen YAML deck for a strategy presentation.
```

### Architecture Deck

```
Generate a pptgen YAML deck explaining a system architecture.
Include sections and image slides where appropriate.
```

### KPI Deck

```
Generate a pptgen deck summarizing operational KPIs.
Use metric_summary slides where possible.
```

---

# Best Practices for AI-Assisted Deck Creation

### Start With Structure

Provide sections whenever possible.

Example:

```
Sections:
- Current State
- Challenges
- Proposed Improvements
- KPIs
```

### Keep Notes Simple

AI works best when notes are simple bullet points.

### Validate Before Building

Always run:

```
validate_pptgen_deck_yaml
```

before generating the final presentation.

### Improve Before Finalizing

Use the improvement skill to polish the deck.

---

# When to Use AI vs Manual YAML

| Scenario | Recommended Approach |
|--------|---------------------|
| quick first draft | AI generation |
| structured templates | manual YAML |
| refining slides | improvement skill |
| debugging YAML | validation skill |

Most teams will combine **AI generation with manual edits**.

---

# Example AI-First Workflow

Many teams will use this workflow.

```
meeting notes
      ↓
generate_pptgen_deck_yaml
      ↓
review YAML
      ↓
improve_pptgen_deck_yaml
      ↓
validate_pptgen_deck_yaml
      ↓
pptgen build
```

This allows teams to move from **ideas to a finished deck in minutes**.

---

# Relationship to Other Documentation

This guide complements the other pptgen documentation.

| Document | Purpose |
|--------|--------|
| Deck Authoring Guide | Manual deck creation |
| AI-Assisted Authoring Guide | Claude workflow |
| Template Authoring Standard | Template rules |
| Deck YAML Schema | Content contract |

---

# Summary

Claude Code skills allow teams to generate, validate, and improve pptgen decks using AI.

Benefits include:

- faster presentation creation
- higher quality slides
- consistent formatting
- structured validation before rendering

The AI-assisted workflow transforms pptgen into a **presentation automation platform**, enabling teams to move quickly from **ideas → slides → presentation**.
