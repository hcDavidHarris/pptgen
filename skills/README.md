
# pptgen Claude Skills

This directory contains Claude Code skills that enable **AI-assisted PowerPoint generation** using the `pptgen` platform.

The skills allow Claude to:

1. Generate structured presentation YAML
2. Validate deck structure and schema
3. Improve slide quality and presentation flow

Together they create an **AI-assisted authoring workflow** that transforms notes or ideas into high-quality PowerPoint presentations.

---

# Overview

The pptgen skills work as a **three-stage pipeline**:

notes / outline
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

Each skill has a specific responsibility.

| Skill | Role |
|-----|-----|
| generate_pptgen_deck_yaml | Create YAML decks from notes or outlines |
| validate_pptgen_deck_yaml | Verify schema and structural correctness |
| improve_pptgen_deck_yaml | Refine slides and improve presentation quality |

---

# Skill Responsibilities

## generate_pptgen_deck_yaml

Purpose:
Convert unstructured input into a valid pptgen deck.

Typical inputs include:
- meeting notes
- strategy outlines
- architecture descriptions
- KPI summaries
- bullet point lists

Example usage:

Use generate_pptgen_deck_yaml to create a pptgen deck from these notes.

Output:

deck.yaml

---

## validate_pptgen_deck_yaml

Purpose:
Ensure a deck follows the pptgen schema and platform rules.

Validation checks include:

- required deck metadata
- supported slide types
- valid slide content structures
- bullet limits
- metric formatting

Example usage:

Use validate_pptgen_deck_yaml on this YAML deck.

Example result:

Validation Result: PASS

or

Validation Result: FAIL  
Missing field: deck.template

---

## improve_pptgen_deck_yaml

Purpose:
Improve the quality of a presentation deck while preserving its meaning.

Typical improvements include:

- simplifying long bullet text
- improving slide titles
- splitting overcrowded slides
- adding logical section breaks
- converting bullet lists to better slide types
- improving narrative flow

Example usage:

Use improve_pptgen_deck_yaml to improve this deck for an executive audience.

---

# Recommended Workflow

Step 1 — Generate YAML

generate_pptgen_deck_yaml

Step 2 — Validate Structure

validate_pptgen_deck_yaml

Step 3 — Improve Presentation

improve_pptgen_deck_yaml

Step 4 — Validate Again

validate_pptgen_deck_yaml

Step 5 — Render the Deck

pptgen build --input deck.yaml

Output:

deck.pptx

---

# When to Use Each Skill

| Situation | Skill |
|----------|------|
| Starting from notes | generate |
| Checking YAML structure | validate |
| Improving slide readability | improve |
| Preparing final deck | validate |

Most real workflows use **all three skills**.

---

# Example End-to-End Session

User:  
Create a deck from these notes about a DevOps strategy.

Claude:  
(generate_pptgen_deck_yaml)

User:  
Validate the deck.

Claude:  
(validate_pptgen_deck_yaml)

User:  
Improve it for executives.

Claude:  
(improve_pptgen_deck_yaml)

User:  
Validate again.

Claude:  
(validate_pptgen_deck_yaml)

Final step:

pptgen build deck.yaml

---

# Relationship to Other Documentation

| Document | Purpose |
|--------|--------|
| Deck Authoring Guide | Manual YAML deck creation |
| AI-Assisted Authoring Guide | Claude workflow |
| Template Authoring Standard | Template rules |
| Deck YAML Schema Specification | Content contract |

---

# Summary

The pptgen skill system enables **AI-assisted presentation generation** through a structured workflow:

Generate → Validate → Improve → Validate → Render

This allows teams to move quickly from **ideas → structured content → presentation-ready slides** while maintaining platform standards.
