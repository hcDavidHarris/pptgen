# Skill: validate_pptgen_deck_yaml

## Purpose

Validate a `pptgen` deck YAML file to ensure it conforms to the platform schema and authoring rules before rendering a PowerPoint presentation.

This skill analyzes YAML structure, field names, slide definitions, and content constraints and returns a structured validation report.

The goal is to catch issues early so that the deck can successfully pass:

```
pptgen validate
pptgen build
```

---

## When to Use

Use this skill when:

- reviewing a newly generated deck YAML
- validating YAML created by AI
- validating YAML created by a human author
- checking schema compliance before building a presentation
- reviewing pull requests that modify deck YAML
- diagnosing build failures from `pptgen`

Do not use this skill to generate decks from ideas. That belongs to the `generate_pptgen_deck_yaml` skill.

---

## Inputs

The skill expects one of the following inputs:

- a YAML deck file
- a YAML snippet containing a `pptgen` deck
- a full YAML document pasted into the conversation
- a path to a YAML file in the repository

Example input:

```yaml
deck:
  title: DevOps Strategy
  template: ops_review_v1
  author: David Harris

slides:
  - type: title
    title: DevOps Strategy
    subtitle: Platform Improvements

  - type: bullets
    title: Strategic Priorities
    bullets:
      - Stabilize pipelines
      - Improve observability
```

---

## Output

Return a structured validation report.

The report should include:

1. overall validation result
2. schema validation
3. slide validation
4. content validation
5. warnings
6. recommended fixes

Example structure:

```
Validation Result: PASS

Schema Validation
✔ deck.title present
✔ deck.template present
✔ slides array present

Slide Validation
✔ slide types valid
✔ bullet slides contain items

Warnings
⚠ bullet slide contains more than 6 bullets

Recommendation
Consider splitting slide into two slides.
```

If errors exist, return **FAIL** with detailed explanation.

---

## Supported Slide Types

The validator must recognize only the following slide types:

```
title
section
bullets
two_column
metric_summary
image_caption
```

Any other slide type is invalid unless explicitly configured elsewhere.

---

## Required Deck Structure

A valid deck must contain:

```yaml
deck:
slides:
```

### Required Deck Fields

```
deck.title
deck.template
deck.author
```

Validation errors must be raised if any of these fields are missing.

---

## Deck Validation Rules

The validator must check the following:

### Deck Object

- `deck` exists
- `deck.title` exists and is not empty
- `deck.template` exists
- `deck.author` exists

### Slides Array

- `slides` exists
- `slides` is an array
- `slides` contains at least one slide

---

## Slide-Level Validation

Each slide must contain:

```
type
```

The value of `type` must match a supported slide type.

If `id` fields exist:

- they must be unique across slides

If `visible` exists:

- it must be boolean

---

## Slide Type Rules

### Title Slide

Required fields:

```
type
title
subtitle
```

Validation checks:

- title must not be empty

---

### Section Slide

Required:

```
type
section_title
```

Optional:

```
section_subtitle
```

---

### Bullet Slide

Required fields:

```
type
title
bullets
```

Validation rules:

- `bullets` must be an array
- `bullets` must contain at least one item
- each bullet must be a string

Warnings:

- more than 6 bullets recommended to split slide

---

### Two Column Slide

Required fields:

```
type
title
left_content
right_content
```

Validation rules:

- both columns must exist
- each column must contain at least one item

---

### Metric Summary Slide

Required fields:

```
type
title
metrics
```

Metric object must contain:

```
label
value
```

Validation rules:

- metrics array must contain at least one metric
- metric values should be strings

---

### Image Caption Slide

Required fields:

```
type
title
image_path
caption
```

Validation rules:

- `image_path` must be a string
- `caption` must not be empty

Optional validation:

- check for relative paths

---

## YAML Naming Convention

All YAML keys must use:

```
lowercase_snake_case
```

Invalid examples:

```
sectionTitle
leftContent
imagePath
```

These must generate validation errors.

---

## Unknown Field Detection

The validator must detect unknown fields.

Example invalid YAML:

```yaml
bullet_list:
```

Correct field:

```yaml
bullets:
```

Unknown fields should produce **ERROR**.

---

## Content Quality Warnings

The validator should also provide non-blocking warnings.

Examples:

### Bullet Density

```
⚠ bullet slide contains 8 bullets
recommend limiting to 4–6
```

### Long Bullet Text

```
⚠ bullet exceeds recommended length
```

### Empty Optional Slides

```
⚠ section slide without subtitle
```

---

## Example PASS Result

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

---

## Example FAIL Result

```
Validation Result: FAIL

Errors
✖ missing deck.template
✖ slide 3 uses unsupported type "bullet_list"
✖ slide 4 bullets array is empty

Warnings
⚠ slide 2 contains 8 bullets
```

---

## Repair Suggestions

When errors occur, the validator should recommend fixes.

Example:

```
Replace:

bullet_list:

With:

bullets:
```

Example:

```
Add required deck field:

deck:
  template: ops_review_v1
```

---

## Behavior Guidelines

The validator should:

- analyze the full YAML structure
- detect structural and semantic errors
- provide precise feedback
- avoid modifying the YAML unless explicitly asked

---

## AI Workflow Integration

Typical workflow:

```
generate_pptgen_deck_yaml
        ↓
validate_pptgen_deck_yaml
        ↓
(optional) improve_pptgen_deck_yaml
        ↓
pptgen build
```

The validator ensures decks are safe to render.

---

## Success Criteria

This skill succeeds when it:

- correctly identifies schema violations
- detects unsupported slide types
- detects missing required fields
- identifies naming convention errors
- provides clear, actionable feedback

The output must help a user quickly repair the YAML so the deck can be rendered successfully.
