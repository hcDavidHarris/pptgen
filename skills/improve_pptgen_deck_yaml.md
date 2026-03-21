
# Skill: improve_pptgen_deck_yaml

## Purpose

Improve an existing pptgen YAML deck so the slides are clearer, more concise,
and better structured for presentation while preserving the original meaning.

This skill acts as a **deck editor and optimizer**.

---

## When to Use

Use this skill when:

• a YAML deck already exists  
• slides feel overcrowded  
• bullet wording is too long  
• slide flow needs improvement  
• the deck should be refined for an executive audience

Do NOT use this skill to create decks from scratch.

---

## Supported Slide Types

The improved deck must only use these slide types:

- title
- section
- bullets
- two_column
- metric_summary
- image_caption

---

## Improvement Goals

### Clarity
- shorten verbose titles
- replace long sentences with concise bullets
- remove redundant wording

### Slide Quality
- keep bullet slides to ~3–6 bullets
- split overcrowded slides
- ensure one idea cluster per slide

### Deck Flow
- group related slides
- introduce section slides when helpful
- improve narrative progression

### Slide Type Optimization
Convert slide types when appropriate:

| Situation | Better Slide Type |
|-----------|------------------|
| KPI lists | metric_summary |
| comparisons | two_column |
| visual explanations | image_caption |

---

## YAML Preservation Rules

The output must remain valid pptgen YAML.

Required structure:

```yaml
deck:
  title: <string>
  template: <string>
  author: <string>

slides:
  - type: <supported_type>
```

Rules:

• preserve valid YAML syntax  
• keep required deck fields  
• avoid unsupported slide types  
• maintain original meaning

---

## Example

Input:

```yaml
- type: bullets
  title: Detailed Overview of Challenges We Are Currently Facing
  bullets:
    - Our deployment pipelines are inconsistent across teams
    - Observability tools vary widely
    - Ownership boundaries are unclear
```

Improved Output:

```yaml
- type: section
  section_title: Current Challenges

- type: bullets
  title: Platform Operations Challenges
  bullets:
    - Fragmented deployment pipelines
    - Inconsistent observability tooling
    - Unclear ownership boundaries
```
