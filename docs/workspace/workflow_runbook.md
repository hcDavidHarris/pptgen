# Workspace Workflow Runbook

Version: 1.0
Owner: Analytics / DevOps Platform Team

This runbook defines the step-by-step procedure for generating a PowerPoint deck using the pptgen workspace model. It covers each stage of the pipeline from input ingestion through rendering.

---

## Overview

```
Input data
    ↓
Step 1: Ingest input
    ↓
Step 2: Create notes
    ↓
Step 3: AI generates YAML deck
    ↓
Step 4: Validate the deck
    ↓
Step 5: Build the presentation
    ↓
Output .pptx
```

---

## Step 1 — Ingest Input

Collect the raw input data for the deck.

### ADO-sourced workflows

Export the relevant Azure DevOps query:

```bash
# Save to workspace
cp sprint_query_export.csv workspace/ado_exports/sprint_24_query.csv
```

Supported export formats: CSV, JSON.

### Meeting note workflows

Create a plain text or markdown summary file:

```bash
workspace/notes/q2_planning_notes.md
```

### Direct metrics workflows

Collect metric values and write them to a notes file or pass them directly as AI input.

---

## Step 2 — Create Notes

If starting from raw ADO exports, convert them to a human-readable summary.

This can be done manually or via AI:

**Manual:** Write a short summary in `workspace/notes/`:

```text
Sprint 24 Summary
Completed: 4 stories
In progress: 2 stories
Blockers: template file not committed
Metrics: 82% completion rate
```

**AI-assisted:** Ask Claude to summarise the ADO export:

```
Summarise this ADO sprint export into a delivery summary.
[paste CSV data or attach file]
```

Save the summary to:

```
workspace/notes/sprint_24_summary.txt
```

---

## Step 3 — AI Generates YAML Deck

Use the appropriate Claude playbook to convert notes into a pptgen YAML deck.

### Select the right playbook

Consult `docs/ai-playbooks/routing_table.yaml` to identify the correct route.

| Input type | Playbook route | Example pattern |
|---|---|---|
| Meeting notes / planning | `meeting_notes_to_eos_rocks` | `examples/eos/eos_rocks.yaml` |
| ADO sprint summary | `ado_summary_to_weekly_delivery` | `examples/engineering_delivery/weekly_delivery_update.yaml` |
| Architecture notes | `architecture_notes_to_adr_deck` | `examples/architecture/adr_template.yaml` |
| DevOps metrics | `devops_metrics_to_scorecard` | `examples/devops/devops_metrics.yaml` |

### Invoke the generation skill

```
Use generate_pptgen_deck_yaml.

Use examples/engineering_delivery/weekly_delivery_update.yaml as the pattern.

[paste sprint summary]

Save the output to workspace/decks/weekly_delivery_update.yaml
```

Claude will produce a YAML deck following the example pattern.

### Save the deck

Save the generated YAML to:

```
workspace/decks/weekly_delivery_update.yaml
```

---

## Step 4 — Validate the Deck

Run the pptgen validator before building.

```bash
pptgen validate --input workspace/decks/weekly_delivery_update.yaml
```

### Expected pass output

```
Validation PASSED (8 slides)
```

### Expected fail output

```
Validation FAILED:
  ERROR: deck.template: 'unknown_template' is not registered in the template registry
```

### Fixing errors

Common fixes:

| Error | Fix |
|---|---|
| `deck.template` not registered | Change to `ops_review_v1` |
| `slides.N.bullets.bullets.0: Input should be a valid string` | Quote items containing colons |
| `metrics: maximum 4 metrics allowed` | Split into two metric_summary slides |
| `Extra inputs are not permitted` | Remove unknown YAML fields |

### Handling warnings

Warnings do not block building. Review and fix where practical:

| Warning | Action |
|---|---|
| `non-string value 1.0 was coerced` | Quote `version: "1.0"` |
| `X bullets — consider splitting` | Split slide at natural break |
| `label is N characters` | Shorten the metric label |

---

## Step 5 — Improve the Deck (optional)

Use the improvement skill to refine slide quality before building:

```
Use improve_pptgen_deck_yaml.

Improve this deck for an engineering leadership audience.

[paste YAML]
```

Then validate again:

```bash
pptgen validate --input workspace/decks/weekly_delivery_update.yaml
```

---

## Step 6 — Build the Presentation

Run the pptgen build command:

```bash
pptgen build --input workspace/decks/weekly_delivery_update.yaml
```

Default output location:

```
output/Weekly_Engineering_Delivery_Update.pptx
```

To specify a custom output path:

```bash
pptgen build \
  --input workspace/decks/weekly_delivery_update.yaml \
  --output workspace/output/sprint_24_update.pptx
```

---

## Complete Weekly Delivery Workflow

End-to-end procedure for weekly engineering delivery updates:

```bash
# 1. Export ADO sprint query
cp sprint_export.csv workspace/ado_exports/sprint_24.csv

# 2. Create summary (manual or AI)
# → workspace/notes/sprint_24_summary.txt

# 3. Generate YAML
# → workspace/decks/weekly_delivery_update.yaml

# 4. Validate
pptgen validate --input workspace/decks/weekly_delivery_update.yaml

# 5. Build
pptgen build --input workspace/decks/weekly_delivery_update.yaml

# 6. Review output
# → output/Weekly_Engineering_Delivery_Update.pptx
```

Total elapsed time (once set up): approximately 5–10 minutes.

---

## Troubleshooting

### pptgen command not found

```bash
pip install -e .
```

or

```bash
pip show pptgen
```

### Template not found error

```
Error: Deck structure is invalid:
  deck.template: 'my_template' is not registered
```

List registered templates:

```bash
pptgen list-templates
```

Use a registered template ID.

### YAML parse error

```
Error: YAML parse error in 'deck.yaml'
```

Check for:
- Incorrect indentation
- Unquoted values containing special characters (`:`, `{`, `[`)
- Tabs instead of spaces

### Output directory does not exist

pptgen creates the output directory automatically. If it fails, create it manually:

```bash
mkdir -p workspace/output
```
