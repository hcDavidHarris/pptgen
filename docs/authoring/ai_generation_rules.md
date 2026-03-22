# AI Generation Rules

Version: 1.0
Owner: Analytics / DevOps Platform Team

This document defines the rules that govern AI-assisted deck generation for the pptgen platform. These rules apply to Claude and any other AI system generating pptgen YAML.

They exist to prevent the most common AI generation failures: invented slide types, malformed YAML, wrong field names, and decks that fail validation before they can be built.

---

## 1. Generation Constraints

### Hard Rules (violations produce invalid decks)

1. Use only supported slide types: `title`, `section`, `bullets`, `two_column`, `metric_summary`, `image_caption`.
2. Do not invent new slide types (e.g. `chart`, `table`, `agenda`, `callout`).
3. Do not use unknown YAML fields. Unknown fields are rejected at parse time.
4. All YAML keys must be `lowercase_snake_case`. Never use `camelCase` or `PascalCase`.
5. Required arrays must not be empty (`bullets: []` is a parse error).
6. `metric_summary` slides must contain **1 to 4 metrics**. Never exceed 4.
7. `metric value` must always be a quoted YAML string. Never emit bare numbers.
8. Every deck must include `deck.title`, `deck.template`, and `deck.author`.
9. The `deck.template` must reference a registered template ID. Default to `ops_review_v1` when not specified.
10. Do not output `null` or empty string for required fields.

### Quality Rules (violations produce warnings or poor slides)

11. Bullets slides should contain **3–6 bullet items**. Avoid exceeding 6.
12. Metric labels should be **40 characters or fewer**.
13. Composed metric values (`value + unit`) should be **20 characters or fewer**.
14. Slide titles should be **60 characters or fewer**.
15. Prefer short, phrase-form bullet text over full sentences.
16. Use section slides to separate logical groups of 2 or more content slides.
17. A title slide should be first unless the user explicitly asks otherwise.

---

## 2. Slide Type Restrictions

Only these types are permitted:

```
title
section
bullets
two_column
metric_summary
image_caption
```

Do not generate:
- `bullet_list` — wrong name, use `bullets`
- `chart` — not supported in Phase 1
- `table` — not supported in Phase 1
- `agenda` — not supported in Phase 1
- `callout` — not supported in Phase 1
- `image` — wrong name, use `image_caption`
- `kpi` — wrong name, use `metric_summary`

---

## 3. Placeholder Restrictions

Do not invent placeholder field names. Only the fields defined per slide type are accepted.

| Slide Type | Accepted Fields |
|---|---|
| `title` | `type`, `title`, `subtitle`, `id`, `notes`, `visible` |
| `section` | `type`, `section_title`, `section_subtitle`, `id`, `notes`, `visible` |
| `bullets` | `type`, `title`, `bullets`, `id`, `notes`, `visible` |
| `two_column` | `type`, `title`, `left_content`, `right_content`, `id`, `notes`, `visible` |
| `metric_summary` | `type`, `title`, `metrics`, `id`, `notes`, `visible` |
| `image_caption` | `type`, `title`, `image_path`, `caption`, `id`, `notes`, `visible` |

`MetricItem` accepted fields: `label`, `value`, `unit`

---

## 4. Ordering Rules

Generate slides in this sequence unless the user specifies otherwise:

1. `title` — always first
2. `section` — opens each logical section
3. Content slides (`bullets`, `two_column`, `metric_summary`, `image_caption`)
4. Additional sections with their content slides
5. Closing metric or summary slide (optional)

Do not place a content slide before the title slide. Do not place a section slide at the very end with no content following it.

---

## 5. YAML Generation Rules

- Output YAML only. Do not wrap in markdown code fences unless the user asks for it.
- Do not emit comments inside YAML unless explicitly requested.
- Do not use YAML anchors or aliases.
- Quote strings that contain colons, special characters, or look like numbers.
- Always quote `version`, metric `value`, and `date` fields.
- Use 2-space indentation consistently.
- Keep YAML clean and minimal — no trailing spaces, no blank lines inside a slide block.

---

## 6. Reasoning Workflow

When converting raw input to a deck:

1. Identify the input type (meeting notes, ADO summary, metrics, architecture notes).
2. Consult `docs/ai-playbooks/routing_table.yaml` to select the correct playbook.
3. Use the referenced `example_pattern` as the structural template.
4. Infer logical sections from the input.
5. Group related ideas into the same slide.
6. Convert long prose into short, slide-friendly phrases.
7. Choose the simplest slide type that fits the content.
8. Add `metric_summary` slides when the input includes quantitative KPIs.
9. Add `two_column` slides for comparisons or before/after structures.
10. Validate mentally before outputting: does every slide use only allowed fields and types?

---

## 7. Example Generation Workflow

```
User provides: sprint summary notes from Azure DevOps

Step 1 — Identify input type: ado_export_summary / sprint_summary
Step 2 — Route: ado_summary_to_weekly_delivery
Step 3 — Use pattern: examples/engineering_delivery/weekly_delivery_update.yaml
Step 4 — Generate YAML following that pattern
Step 5 — Output only the YAML
Step 6 — User runs: pptgen validate --input deck.yaml
Step 7 — User runs: pptgen build --input deck.yaml
```

---

## 8. Template Defaults

When the user does not specify a template, use:

```yaml
template: ops_review_v1
```

When the user specifies a template, use it exactly as written.

---

## 9. Output Contract

The generated YAML must:

- Conform to the `DeckFile` schema (deck + slides)
- Pass `pptgen validate` without errors
- Use only supported slide types
- Be human-readable and editable
- Reflect the user's intent without overengineering

The generated YAML must not:

- Invent slide types
- Use unknown or camelCase field names
- Produce empty required arrays
- Leave required string fields null or empty
- Include unsupported structural elements

---

## 10. References

| Document | Purpose |
|---|---|
| [authoring_contract.md](../architecture/authoring_contract.md) | Canonical field and schema rules |
| [slide_type_reference.md](slide_type_reference.md) | Per-type field reference |
| [routing_table.yaml](../ai-playbooks/routing_table.yaml) | Input → playbook routing |
| `examples/` | Reference YAML patterns per use case |
