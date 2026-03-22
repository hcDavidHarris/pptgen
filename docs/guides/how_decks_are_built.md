# How Decks Are Built

Version: 1.0
Owner: Analytics / DevOps Platform Team

This guide explains the full journey from input source to PowerPoint file. It covers where content comes from, how a playbook is selected, how YAML is generated, how validation works, and how the renderer turns it all into slides.

---

## Overview

```
Input Source
    ↓
Playbook Selection
    ↓
YAML Generation
    ↓
Validation
    ↓
Rendering
    ↓
PowerPoint
```

---

## Stage 1: Input Sources

Decks can originate from several types of input:

| Input Type | Example | Routing Route |
|---|---|---|
| Azure DevOps export | Sprint query CSV, feature status | `ado_summary_to_weekly_delivery` |
| Meeting notes | EOS planning session notes | `meeting_notes_to_eos_rocks` |
| Architecture notes | ADR summary, design review | `architecture_notes_to_adr_deck` |
| DevOps metrics | DORA metrics, CI/CD stats | `devops_metrics_to_scorecard` |
| Manual authoring | Direct YAML editing | n/a |

Inputs are stored in `workspace/notes/` or `workspace/ado_exports/` before being processed.

---

## Stage 2: Playbook Selection

Before generating YAML, select the right playbook using `docs/ai-playbooks/routing_table.yaml`.

The routing table maps:

```
input_type → playbook → example_pattern → output_yaml
```

**How to select:**
1. Identify the input type (sprint summary, meeting notes, metrics, etc.).
2. Find the matching `route_id` in `routing_table.yaml`.
3. Note the `example_pattern` path — this is the structural guide for generation.
4. Note the `output_yaml` path — this is where to save the generated deck.

If no route matches exactly, use the closest example library and apply `generate_pptgen_deck_yaml`.

---

## Stage 3: YAML Generation

YAML decks are generated either manually or through the Claude `generate_pptgen_deck_yaml` skill.

### AI Generation

The skill prompt references the example pattern:

```
Use generate_pptgen_deck_yaml.
Use examples/engineering_delivery/weekly_delivery_update.yaml as the pattern.

[paste input content]
```

Claude follows `docs/authoring/ai_generation_rules.md` to:
- Use only supported slide types
- Follow `lowercase_snake_case` field naming
- Quote numeric values
- Respect the 4-metric and 6-bullet limits
- Open with a title slide
- Organise content into logical sections

### Manual Authoring

See [docs/authoring/yaml_authoring_guide.md](../authoring/yaml_authoring_guide.md) for field reference.

Use `pptgen deck scaffold` to generate a starter template:

```bash
pptgen deck scaffold --type engineering_delivery --output workspace/decks/my_deck.yaml
```

---

## Stage 4: Validation

Every deck must pass validation before being built.

```bash
pptgen validate --input workspace/decks/my_deck.yaml
```

### What validation checks

**Hard errors (block build):**
- `deck.template` registered in `templates/registry.yaml`
- Template status is `approved`
- Slide IDs are unique
- `metric_summary` has ≤4 metrics
- Pydantic structural checks (required fields, no unknown fields, non-empty arrays)

**Warnings (do not block):**
- `version` or metric `value` not quoted as strings
- Bullets slide has >6 items
- Metric label >40 characters
- Composed metric value >20 characters

Use `--explain` for detailed guidance on any error or warning:

```bash
pptgen validate --input workspace/decks/my_deck.yaml --explain
```

### Validation pipeline internals

```
load_deck(path)
    yaml_loader reads file
    Pydantic DeckFile validates schema
    Returns (DeckFile, raw_dict)
        ↓
validate_deck(deck, registry, raw_dict)
    Registry check
    Slide ID uniqueness
    Per-slide semantic checks
    Coercion detection from raw_dict
    Returns ValidationResult(valid, errors, warnings)
```

---

## Stage 5: Rendering

Once validation passes, `pptgen build` renders the deck to PowerPoint.

```bash
pptgen build --input workspace/decks/my_deck.yaml
```

### What the renderer does

```
1. load_template(template_path)
      Opens the .pptx template file via python-pptx

2. inspect_template(prs)
      Maps layout names ("Bullets Layout") → SlideLayout objects

3. For each visible slide in deck.slides:
      a. layout = inspection.get_layout(SLIDE_TYPE_TO_LAYOUT[slide.type])
      b. pptx_slide = prs.slides.add_slide(layout)
      c. rename placeholders by placeholder_format.idx → UPPERCASE_SNAKE_CASE
      d. copy lstStyle from layout (text colour inheritance fix)
      e. renderer = SLIDE_RENDERERS[slide.type]
      f. renderer(slide_model, pptx_slide)
            placeholder_mapper.set_text("TITLE", slide.title)
            placeholder_mapper.set_bullets("BULLETS", slide.bullets)
            ...

4. prs.save(output_path)
```

### Slide type → layout mapping

| Slide type | Layout name |
|---|---|
| `title` | Title Layout |
| `section` | Section Layout |
| `bullets` | Bullets Layout |
| `two_column` | Two Column Layout |
| `metric_summary` | Metric Summary Layout |
| `image_caption` | Image Caption Layout |

### Placeholder writing

Renderers call `set_text(slide, "PLACEHOLDER_NAME", value)` and `set_bullets(slide, "PLACEHOLDER_NAME", list)`. The mapper finds shapes by their `UPPERCASE_SNAKE_CASE` name attribute.

---

## Stage 6: Output

The generated PowerPoint file is saved to `output/` by default:

```
output/<deck_title_with_underscores>.pptx
```

Use `--output` to control the path:

```bash
pptgen build \
  --input workspace/decks/weekly_delivery.yaml \
  --output workspace/output/sprint_24_update.pptx
```

---

## End-to-End Summary

```
workspace/notes/sprint_24_summary.txt
    ↓ generate_pptgen_deck_yaml
workspace/decks/weekly_delivery_update.yaml
    ↓ pptgen validate
ValidationResult: PASSED
    ↓ pptgen build
output/Weekly_Engineering_Delivery_Update.pptx
```
