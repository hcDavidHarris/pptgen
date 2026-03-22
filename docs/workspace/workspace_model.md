# Workspace Model

Version: 1.0
Owner: Analytics / DevOps Platform Team

This document defines the workspace directory structure used for pptgen deck generation. The workspace is the **operational layer** of the pptgen platform — it holds inputs, intermediate artifacts, and generated output. It lives outside the pptgen repository.

---

## Core Principle

The pptgen repository provides the engine, templates, and examples. The workspace contains everything that is specific to a team's actual operations.

| Layer | Location | Contains |
|---|---|---|
| Platform | pptgen repository | Engine, templates, examples, documentation |
| Workspace | Outside repository | Inputs, notes, YAML decks, output files |

Keeping them separate ensures:
- The pptgen repository stays clean and deterministic
- Operational data is never committed to the platform repo
- Teams can run workflows repeatedly without polluting the codebase

---

## Directory Structure

```
workspace/
├─ ado_exports/    ← raw data from external systems
├─ notes/          ← structured summaries and meeting notes
├─ decks/          ← generated pptgen YAML deck files
├─ validated/      ← YAML decks that have passed validation (optional staging area)
└─ output/         ← generated .pptx presentation files
```

---

## Directory Responsibilities

### ado_exports/

Raw operational data exported from external systems.

Typical contents:
- Azure DevOps sprint query exports (CSV, JSON)
- Feature status reports
- Backlog snapshots
- Blocker and risk exports
- DORA metrics exports

These files are **input sources**. They are not modified in place — they are consumed to produce notes or used directly by AI playbooks.

Example files:
```
ado_exports/
├─ sprint_24_query.csv
├─ feature_status_2026-03-22.csv
├─ backlog_snapshot.json
└─ blockers.json
```

---

### notes/

Human-readable or AI-generated summaries derived from raw data or meeting sessions.

Typical contents:
- Sprint review summaries
- Weekly delivery digests
- Meeting notes from EOS sessions
- Architecture decision notes
- AI-generated summaries from ADO exports

These notes are the **primary input to AI deck generation**. They are usually one or a few paragraphs of structured text.

Example files:
```
notes/
├─ sprint_24_summary.txt
├─ weekly_delivery_2026-03-22.txt
├─ q2_planning_notes.md
└─ adr_event_streaming.md
```

---

### decks/

pptgen YAML deck definitions. These are either AI-generated (from notes) or manually authored.

These files are validated and then rendered into PowerPoint presentations.

Example files:
```
decks/
├─ weekly_delivery_update.yaml
├─ eos_rocks_q2.yaml
├─ devops_metrics_march.yaml
└─ architecture_adr_001.yaml
```

---

### validated/

Optional staging area for YAML decks that have passed `pptgen validate`. Separating validated decks from draft decks makes build workflows more reliable.

Some teams skip this directory and build directly from `decks/`.

---

### output/

Generated PowerPoint files produced by `pptgen build`.

Example files:
```
output/
├─ weekly_delivery_update.pptx
├─ eos_rocks_q2.pptx
├─ devops_metrics_march.pptx
└─ architecture_adr_001.pptx
```

These files are used for:
- Leadership updates
- Sprint review presentations
- Architecture review sessions
- Delivery reporting

---

## Artifact Lifecycle

```
ADO export / meeting notes
          ↓
    ado_exports/ or notes/
          ↓
    AI generates YAML
          ↓
        decks/
          ↓
    pptgen validate
          ↓
      validated/           (optional staging)
          ↓
    pptgen build
          ↓
       output/
```

---

## Naming Conventions

### Deck files

Use descriptive names with date or sprint suffix:

```
weekly_delivery_update_2026-03-22.yaml
eos_rocks_q2_2026.yaml
devops_metrics_march_2026.yaml
sprint_24_summary.yaml
```

Pattern: `<deck_type>_<context>_<date_or_sprint>.yaml`

### Output files

Output filename is derived automatically from `deck.title` by the CLI:

```
deck.title: "Weekly Engineering Delivery Update"
→ output: Weekly_Engineering_Delivery_Update.pptx
```

Use `--output` to override the default path:

```bash
pptgen build --input decks/sprint_24.yaml --output output/sprint_24_review.pptx
```

---

## Version Control

The workspace should **not** be committed to the pptgen repository. Workspace artifacts often contain operational data, delivery plans, and internal project details that are environment-specific.

Recommended workspace location:

```
~/pptgen_workspace/
```

or

```
/projects/<team>/pptgen_workspace/
```

Multi-user teams may maintain individual workspaces:

```
/Users/david/pptgen_workspace/
/Users/alex/pptgen_workspace/
```

---

## Initialising a Workspace

Use the CLI to scaffold the workspace directory structure:

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

See [quickstart.md](quickstart.md) for a step-by-step first-deck workflow.
