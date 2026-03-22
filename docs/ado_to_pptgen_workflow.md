
# ADO-to-pptgen Workflow
### Turning Azure DevOps Delivery Data into Presentation Artifacts

Version: 1.0  
Owner: Analytics / DevOps Platform Team  

---

# Purpose

This workflow explains how to use **Azure DevOps (ADO)** data together with **AI-assisted authoring** and **pptgen** to generate recurring engineering delivery presentations.

The goal is to transform delivery data such as:

- features
- user stories
- tasks
- backlog summaries
- sprint status
- blockers

into **structured YAML decks** that can be rendered into PowerPoint presentations.

---

# High-Level Flow

The recommended process is:

Azure DevOps data  
↓  
Export / query / summary  
↓  
Workspace input files  
↓  
AI converts delivery state into YAML  
↓  
pptgen validates YAML  
↓  
pptgen renders PowerPoint deck  

This keeps the platform clean and deterministic:

- ADO provides operational data  
- AI interprets and structures it  
- pptgen renders the deck  

---

# Core Principle

pptgen should **not** parse raw ADO data directly in Phase 1 or Phase 2.

Instead, the system should use a **structured intermediate layer**:

ADO → notes / exports → AI → YAML → pptgen

This separation creates:

- deterministic builds  
- simpler testing  
- cleaner architecture  
- easier reuse across use cases  

---

# Recommended Workspace Structure

Use a working directory outside the repo or in a team workspace.

Example:

workspace/
├─ ado_exports/
│  ├─ features.json
│  ├─ user_stories.json
│  ├─ tasks.json
│  └─ blockers.json
│
├─ notes/
│  ├─ sprint_summary.txt
│  └─ delivery_highlights.txt
│
├─ decks/
│  ├─ weekly_delivery_update.yaml
│  ├─ sprint_summary.yaml
│  └─ backlog_health.yaml
│
└─ output/
   ├─ weekly_delivery_update.pptx
   └─ sprint_summary.pptx

This lets the team separate:

- raw operational input  
- human/AI working notes  
- final YAML decks  
- rendered slide artifacts  

---

# Step 1 — Extract ADO Data

The process begins with one or more of the following:

- ADO query exports  
- sprint board summaries  
- backlog snapshots  
- work item lists  
- feature status exports  
- blocker lists  

Typical useful data includes:

- feature title  
- work item state  
- owner  
- sprint name  
- completion status  
- blocked items  
- due dates  
- priority  

This data may be exported as:

- CSV  
- JSON  
- text summaries  
- copied query results  

---

# Step 2 — Summarize the Delivery State

Before generating YAML, create a delivery summary.

This may be:

- manual notes  
- AI-generated summary from ADO export  
- meeting notes from sprint review  
- copied highlights from ADO query results  

Example summary:

Sprint 24 Summary

Completed:
- Renderer hardening complete
- New template inventory docs published
- Example libraries expanded

In Progress:
- Template validator
- Placeholder diagnostics

Blocked:
- One template dependency still manual
- ADO ingestion workflow not yet implemented

Metrics:
- Features completed: 4
- Stories in progress: 18
- Blocked items: 2
- Weekly completion: 82%

Save this in:

workspace/notes/sprint_summary.txt

---

# Step 3 — Ask AI to Convert Summary into YAML

Use AI to convert the structured summary into a pptgen deck.

Example prompt:

Convert this Azure DevOps sprint summary into a pptgen YAML deck.

Use the engineering_delivery/weekly_delivery_update.yaml example as a pattern.

Requirements:
- include a title slide
- include highlights
- include blockers
- include a metric_summary slide
- keep the deck concise and leadership-friendly

This step produces a YAML file such as:

workspace/decks/weekly_delivery_update.yaml

---

# Step 4 — Validate the YAML Deck

Before rendering, validate the generated YAML.

Run:

pptgen validate --input workspace/decks/weekly_delivery_update.yaml

Validation checks:

- required deck fields  
- valid slide types  
- supported template reference  
- valid metric_summary contract  
- deck structure correctness  

---

# Step 5 — Render the PowerPoint Deck

Once the YAML validates, build the deck.

Run:

pptgen build --input workspace/decks/weekly_delivery_update.yaml

Recommended output:

workspace/output/weekly_delivery_update.pptx

---

# Common ADO-to-pptgen Use Cases

## Weekly Delivery Update
Use for completed work, in-progress stories, blockers, and metrics.

## Sprint Summary
Summarize sprint outcomes and next sprint focus.

## Backlog Health
Track backlog size, intake trends, and blocked work.

## Feature Delivery Status
Report progress across major engineering features.

## Risks and Blockers
Highlight delivery risks and mitigation strategies.

---

# Best Practices

## Keep ADO Inputs Focused
Export only the data required for the deck.

## Use AI for Narrative Compression
ADO data is detailed; slides should be concise.

## Keep YAML Deterministic
Always generate YAML first, then validate and render.

## Use Example Libraries
Ask AI to follow existing YAML examples to improve consistency.

---

# Future State Vision

Future automation pipeline:

ADO query  
↓  
automated export  
↓  
AI summarizes delivery state  
↓  
generate YAML deck  
↓  
pptgen build  
↓  
weekly delivery slides  

This allows teams to produce leadership-ready updates in minutes.

---

# Summary

The ADO-to-pptgen workflow converts **Azure DevOps delivery data into structured presentation artifacts**.

Architecture:

ADO data → notes / exports → AI → YAML → pptgen → PowerPoint

Responsibilities remain clear:

- ADO provides operational data  
- AI converts data into structured narrative  
- pptgen renders repeatable presentation artifacts  

This workflow supports:

- weekly delivery updates  
- sprint reviews  
- backlog health reviews  
- feature delivery reporting  
- blocker and risk reporting
