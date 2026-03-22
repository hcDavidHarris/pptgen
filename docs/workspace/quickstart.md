# Workspace Quickstart

Get up and running with the pptgen workspace model in minutes.

---

## Prerequisites

- pptgen installed: `pip install -e .` from the repo root
- Python 3.11+

Verify installation:

```bash
pptgen --help
```

---

## Step 1 — Initialise the Workspace

```bash
pptgen workspace init
```

This creates:

```
workspace/
├─ ado_exports/
├─ notes/
├─ decks/
├─ validated/
└─ output/
```

---

## Step 2 — Generate Your First Deck

Use an example from the repository as your starting point.

### Option A — Copy an example and edit it

```bash
cp examples/engineering_delivery/weekly_delivery_update.yaml workspace/decks/my_first_deck.yaml
```

Edit `workspace/decks/my_first_deck.yaml` with your content.

### Option B — Use AI generation

Paste your notes or sprint summary into Claude and use the generate skill:

```
Use generate_pptgen_deck_yaml.

Use examples/engineering_delivery/weekly_delivery_update.yaml as the pattern.

My sprint this week:
- Completed 3 features
- 2 stories in progress
- One blocker: missing API credentials
- Metrics: 75% completion rate

Save output to workspace/decks/my_first_deck.yaml
```

---

## Step 3 — Validate the Deck

```bash
pptgen validate --input workspace/decks/my_first_deck.yaml
```

Expected output:

```
Validation PASSED (N slides)
```

Fix any errors reported before proceeding. See [workflow_runbook.md](workflow_runbook.md) for common fixes.

---

## Step 4 — Build the Presentation

```bash
pptgen build --input workspace/decks/my_first_deck.yaml
```

Your PowerPoint file will be at:

```
output/<deck_title>.pptx
```

---

## What's Next

- Review example decks in `examples/` for patterns to follow
- Read [workspace_model.md](workspace_model.md) for the full workspace directory reference
- Read [workflow_runbook.md](workflow_runbook.md) for step-by-step guidance per workflow type
- Read [docs/authoring/yaml_authoring_guide.md](../authoring/yaml_authoring_guide.md) to write YAML manually
- Read [docs/ai-playbooks/README.md](../ai-playbooks/README.md) for AI-assisted workflow patterns
