
# ADO Query Examples for Engineering Delivery Decks

This document provides sample Azure DevOps (ADO) query patterns that map directly to the `engineering_delivery` YAML example decks in the pptgen repository.

These examples help teams move from:

ADO data → summary → YAML deck → pptgen → PowerPoint

The queries below are patterns rather than strict schemas because ADO fields vary across organizations.

---

# Recommended Workflow

1. Run or export the relevant ADO query
2. Summarize results into a short note
3. Use AI to convert the summary into a pptgen YAML deck
4. Run `pptgen validate`
5. Run `pptgen build`

---

# 1. Sprint Summary Deck

Related YAML deck:

examples/engineering_delivery/sprint_summary.yaml

Purpose: Summarize current sprint progress, completed work, blocked work, and next sprint focus.

Recommended ADO Query:

Iteration Path = Current Sprint  
Work Item Type IN (User Story, Feature, Task, Bug)  
State IN (New, Active, Resolved, Closed)

Useful Fields:

- ID
- Title
- Work Item Type
- State
- Assigned To
- Iteration Path
- Tags
- Parent
- Remaining Work
- Story Points

Example Summary:

Sprint Summary

Completed:
- 6 stories closed
- renderer hardening completed

In Progress:
- 4 active stories

Blocked:
- 1 dependency blocked by template design

Metrics:
Stories Completed: 6
Stories In Progress: 4
Blocked Items: 1
Sprint Completion: 78%

---

# 2. Feature Delivery Status Deck

Related YAML deck:

examples/engineering_delivery/feature_delivery_status.yaml

Purpose: Show feature-level progress across completed, in-progress, and planned work.

Recommended Query:

Work Item Type = Feature  
State != Removed

Useful Fields:

- ID
- Title
- State
- Assigned To
- Iteration Path
- Tags
- Business Value
- Priority
- Target Date

Example Summary:

Completed:
- YAML loader and validation
- Template registry
- Rendering engine MVP

In Progress:
- Template compatibility validator

Planned:
- ADO workflow integration

---

# 3. Backlog Health Deck

Related YAML deck:

examples/engineering_delivery/backlog_health.yaml

Purpose: Track backlog size, intake trends, and blocked work.

Recommended Query:

Work Item Type IN (Feature, User Story, Task)  
State IN (New, Active, Approved, Committed)

Useful Fields:

- ID
- Title
- Work Item Type
- State
- Assigned To
- Iteration Path
- Tags
- Priority
- Blocked
- Created Date

Example Metrics:

Open Features: 12  
Active Stories: 34  
Tasks Completed This Week: 27  
Blocked Items: 3

Example Narrative:

- Active story volume manageable
- Blocked work concentrated in two dependencies
- Feature intake rising faster than close rate

---

# 4. Weekly Delivery Update Deck

Related YAML deck:

examples/engineering_delivery/weekly_delivery_update.yaml

Purpose: Provide weekly leadership updates summarizing delivery progress.

Recommended Query:

Changed Date >= Today - 7 days  
Work Item Type IN (Feature, User Story, Task, Bug)

Useful Fields:

- ID
- Title
- State
- Changed Date
- Assigned To
- Parent Feature
- Tags

Example Summary:

Weekly Highlights:
- 4 platform features completed
- renderer stabilized
- example library expanded

Current Blockers:
- manual template dependency
- CLI ergonomics still improving

Metrics:
Features Completed: 4  
Active Stories: 18  
Blocked Items: 2  
Weekly Completion: 82%

---

# 5. Risks and Blockers Deck

Related YAML deck:

examples/engineering_delivery/risks_and_blockers.yaml

Purpose: Highlight delivery risks and unresolved blockers.

Recommended Query:

Blocked = True  
OR Tags contains (blocked, dependency, risk)  
State != Closed

Useful Fields:

- ID
- Title
- State
- Assigned To
- Tags
- Blocked
- Due Date
- Changed Date

Example Summary:

Top Risks:
- template creation remains manual
- example drift risk
- ADO integration not yet implemented

Current Blockers:
- missing template validator
- workspace workflow still being defined

---

# AI Prompt Pattern

Example prompt for generating YAML:

Convert this Azure DevOps delivery summary into a pptgen YAML deck.

Use examples/engineering_delivery/weekly_delivery_update.yaml as the pattern.

Requirements:
- include title slide
- include highlights
- include blockers
- include delivery metrics
- keep the deck concise

---

# Suggested Workspace Structure

workspace/
├─ ado_exports/
│  ├─ sprint_query.csv
│  ├─ feature_status.csv
│  ├─ backlog_health.csv
│  └─ blockers.csv
│
├─ notes/
│  ├─ sprint_summary.txt
│  ├─ weekly_delivery_summary.txt
│  └─ blocker_summary.txt
│
├─ decks/
│  ├─ sprint_summary.yaml
│  ├─ weekly_delivery_update.yaml
│  └─ backlog_health.yaml
│
└─ output/
   ├─ sprint_summary.pptx
   ├─ weekly_delivery_update.pptx
   └─ backlog_health.pptx

---

# Summary

These ADO query patterns help teams connect Azure DevOps operational data to the engineering_delivery deck library.

Pipeline:

ADO → summary → YAML → validate → pptgen → slides

This supports:

- sprint reviews
- weekly delivery updates
- backlog health reporting
- feature delivery tracking
- blocker and risk reporting
