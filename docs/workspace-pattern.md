# Workspace Pattern

This document defines the recommended **workspace structure** for teams using pptgen.

The workspace is where operational inputs, intermediate artifacts, and generated slide decks live. It is intentionally **separate from the pptgen repository**.

Keeping the workspace separate ensures that:

- the pptgen codebase remains clean and deterministic
- operational data is not committed to git
- teams can run pptgen workflows repeatedly without polluting the repository

---

# Core Principle

The pptgen repository contains:

- the rendering engine
- templates
- YAML schema definitions
- documentation
- example libraries

The workspace contains:

- operational inputs
- meeting notes
- Azure DevOps exports
- generated YAML decks
- generated PowerPoint files

This separation keeps responsibilities clear.

```text
pptgen platform → workspace data → pptgen build → slide artifacts
```

---

# Recommended Workspace Structure

A typical workspace should follow this structure:

```text
workspace/
├─ ado_exports/
├─ notes/
├─ decks/
└─ output/
```

Each directory has a specific purpose.

---

# Directory Responsibilities

## ado_exports/

Contains raw operational data exported from external systems such as:

- Azure DevOps queries
- backlog snapshots
- feature status exports
- task lists
- blocker reports

Typical files:

```text
ado_exports/
├─ sprint_query.csv
├─ feature_status.csv
├─ backlog_snapshot.csv
└─ blockers.json
```

These files are **input data sources** used to produce deck summaries.

---

## notes/

Contains structured or semi-structured summaries derived from operational data.

These may be:

- manual notes
- meeting summaries
- AI-generated summaries
- sprint review notes
- delivery highlights

Example:

```text
notes/
├─ sprint_summary.txt
├─ weekly_delivery_summary.txt
└─ backlog_summary.txt
```

These notes are typically converted into YAML deck definitions using AI.

---

## decks/

Contains pptgen YAML deck definitions.

These files represent the **structured presentation content** used by the pptgen engine.

Example:

```text
decks/
├─ sprint_summary.yaml
├─ weekly_delivery_update.yaml
└─ backlog_health.yaml
```

These YAML files are validated and then rendered into PowerPoint presentations.

---

## output/

Contains generated presentation artifacts.

These files are produced by the `pptgen build` command.

Example:

```text
output/
├─ sprint_summary.pptx
├─ weekly_delivery_update.pptx
└─ backlog_health.pptx
```

These files are typically used for:

- leadership updates
- sprint reviews
- delivery reporting
- architecture reviews

---

# End-to-End Workflow

The workspace supports the following workflow:

```text
Azure DevOps data
        ↓
ado_exports/
        ↓
notes/
        ↓
AI converts notes into YAML
        ↓
decks/
        ↓
pptgen validate
        ↓
pptgen build
        ↓
output/
```

This architecture keeps each stage of the process clear and reproducible.

---

# Example Workflow

Example weekly delivery workflow:

1. Export ADO sprint query

```text
workspace/ado_exports/sprint_query.csv
```

2. Create a summary

```text
workspace/notes/sprint_summary.txt
```

3. Ask AI to convert the summary into YAML

```text
workspace/decks/weekly_delivery_update.yaml
```

4. Validate the deck

```bash
pptgen validate --input workspace/decks/weekly_delivery_update.yaml
```

5. Generate the PowerPoint deck

```bash
pptgen build --input workspace/decks/weekly_delivery_update.yaml
```

6. Review the output

```text
workspace/output/weekly_delivery_update.pptx
```

---

# Using Example Libraries

When generating YAML decks with AI, reference the example libraries included in the repository.

Example:

```text
examples/engineering_delivery/weekly_delivery_update.yaml
```

Prompt pattern:

```text
Use examples/engineering_delivery/weekly_delivery_update.yaml as a pattern.

Convert the following sprint summary into a pptgen YAML deck.
```

This greatly improves consistency.

---

# Git and Version Control

The workspace should **not be committed to the pptgen repository**.

Workspace artifacts often contain:

- operational data
- delivery plans
- internal project details

These files are environment-specific and should remain outside version control.

Typical setup:

```text
~/pptgen_workspace
```

or

```text
/projects/team_workspace/pptgen
```

---

# Multi-User Workspaces

Each team member may maintain their own workspace.

Example:

```text
/Users/david/pptgen_workspace
/Users/alex/pptgen_workspace
```

The pptgen platform repository remains shared while workspaces remain local.

---

# Optional Future CLI Support

Future versions of pptgen may include a helper command:

```text
pptgen init-workspace
```

Which would automatically generate:

```text
workspace/
├─ ado_exports/
├─ notes/
├─ decks/
└─ output/
```

This would simplify onboarding for new users.

---

# Summary

The workspace pattern provides a clean separation between:

| Layer | Responsibility |
|------|---------------|
| pptgen repository | platform, templates, examples |
| workspace | operational data and generated artifacts |

The complete pipeline becomes:

```text
ADO → exports → notes → YAML → pptgen → slides
```

This structure supports repeatable workflows for:

- sprint reviews
- weekly delivery updates
- backlog health reporting
- architecture updates
- engineering leadership presentations
