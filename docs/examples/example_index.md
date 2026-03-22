# Example Deck Index

Version: 1.0
Owner: Analytics / DevOps Platform Team

This index maps common presentation scenarios to the right example deck, playbook, and AI routing route. Use it to find the best starting point for a new deck.

---

## How to Use

1. Find your scenario in the table below.
2. Note the example pattern file.
3. Copy the example: `pptgen example copy <name> --output workspace/decks/<name>.yaml`
4. Or use AI generation with the matching playbook.

---

## Scenario Index

| Scenario | Example File | Library | Playbook Route | AI Route ID |
|---|---|---|---|---|
| Weekly engineering delivery update | `weekly_delivery_update` | engineering_delivery | [ado-summary-to-weekly-delivery.md](../ai-playbooks/ado-summary-to-weekly-delivery.md) | `ado_summary_to_weekly_delivery` |
| Sprint summary report | `sprint_summary` | engineering_delivery | [ado-summary-to-weekly-delivery.md](../ai-playbooks/ado-summary-to-weekly-delivery.md) | `ado_summary_to_weekly_delivery` |
| Feature delivery status | `feature_delivery_status` | engineering_delivery | [ado-summary-to-weekly-delivery.md](../ai-playbooks/ado-summary-to-weekly-delivery.md) | `ado_summary_to_weekly_delivery` |
| Backlog health report | `backlog_health` | engineering_delivery | [ado-summary-to-weekly-delivery.md](../ai-playbooks/ado-summary-to-weekly-delivery.md) | `ado_summary_to_weekly_delivery` |
| Risks and blockers report | `risks_and_blockers` | engineering_delivery | [ado-summary-to-weekly-delivery.md](../ai-playbooks/ado-summary-to-weekly-delivery.md) | `ado_summary_to_weekly_delivery` |
| EOS quarterly rocks | `eos_rocks` | eos | [meeting-notes-to-eos-rocks.md](../ai-playbooks/meeting-notes-to-eos-rocks.md) | `meeting_notes_to_eos_rocks` |
| EOS weekly scorecard | `eos_scorecard` | eos | [meeting-notes-to-eos-rocks.md](../ai-playbooks/meeting-notes-to-eos-rocks.md) | `meeting_notes_to_eos_rocks` |
| EOS issues list | `eos_issues_list` | eos | [meeting-notes-to-eos-rocks.md](../ai-playbooks/meeting-notes-to-eos-rocks.md) | `meeting_notes_to_eos_rocks` |
| EOS Vision/Traction Organizer | `eos_vto` | eos | [meeting-notes-to-eos-rocks.md](../ai-playbooks/meeting-notes-to-eos-rocks.md) | `meeting_notes_to_eos_rocks` |
| EOS quarterly review | `eos_quarterly_review` | eos | [meeting-notes-to-eos-rocks.md](../ai-playbooks/meeting-notes-to-eos-rocks.md) | `meeting_notes_to_eos_rocks` |
| DORA / DevOps metrics scorecard | `devops_metrics` | devops | [devops-metrics-to-scorecard.md](../ai-playbooks/devops-metrics-to-scorecard.md) | `devops_metrics_to_scorecard` |
| DevOps transformation roadmap | `devops_transformation` | devops | [devops-metrics-to-scorecard.md](../ai-playbooks/devops-metrics-to-scorecard.md) | `devops_metrics_to_scorecard` |
| DevOps Three Ways overview | `devops_three_ways` | devops | [devops-metrics-to-scorecard.md](../ai-playbooks/devops-metrics-to-scorecard.md) | `devops_metrics_to_scorecard` |
| Deployment pipeline overview | `devops_pipeline` | devops | [devops-metrics-to-scorecard.md](../ai-playbooks/devops-metrics-to-scorecard.md) | `devops_metrics_to_scorecard` |
| Team Topologies overview | `team_types` | team_topologies | *(no specific playbook)* | use `generate_pptgen_deck_yaml` |
| Platform team model | `platform_team_model` | team_topologies | *(no specific playbook)* | use `generate_pptgen_deck_yaml` |
| Architecture overview | `architecture_overview` | root | [architecture-notes-to-adr-deck.md](../ai-playbooks/architecture-notes-to-adr-deck.md) | `architecture_notes_to_adr_deck` |
| Architecture Decision Record | `adr_template` | architecture | [architecture-notes-to-adr-deck.md](../ai-playbooks/architecture-notes-to-adr-deck.md) | `architecture_notes_to_adr_deck` |
| Executive leadership update | `executive_update` | root | *(no specific playbook)* | use `generate_pptgen_deck_yaml` |
| KPI dashboard | `kpi_dashboard` | root | [devops-metrics-to-scorecard.md](../ai-playbooks/devops-metrics-to-scorecard.md) | `devops_metrics_to_scorecard` |
| Product strategy | `product_strategy` | root | *(no specific playbook)* | use `generate_pptgen_deck_yaml` |
| Weekly ops report | `weekly_ops_report` | root | [ado-summary-to-weekly-delivery.md](../ai-playbooks/ado-summary-to-weekly-delivery.md) | `ado_summary_to_weekly_delivery` |

---

## Library Descriptions

### engineering_delivery

Sprint-based engineering delivery decks sourced from Azure DevOps. Designed for weekly team updates, sprint reviews, and backlog reporting to engineering leadership.

```bash
pptgen example list --library engineering_delivery
```

### eos

EOS (Entrepreneurial Operating System) operational cadence artifacts. Covers rocks, scorecard, VTO, issues list, and quarterly review. Used by leadership teams running on EOS.

```bash
pptgen example list --library eos
```

### devops

DevOps Handbook and DORA metrics-based decks. Used for engineering scorecard presentations, transformation roadmaps, and platform capability reviews.

```bash
pptgen example list --library devops
```

### team_topologies

Team Topologies-inspired organizational design decks. Covers team types, interaction modes, cognitive load, and platform team models.

```bash
pptgen example list --library team_topologies
```

### Root examples

Generic examples for common presentation types not tied to a specific operational workflow.

```bash
pptgen example list --library root
```

---

## Quick Copy Commands

```bash
# Weekly delivery update
pptgen example copy weekly_delivery_update --output workspace/decks/weekly_delivery_update.yaml

# EOS quarterly rocks
pptgen example copy eos_rocks --output workspace/decks/eos_rocks.yaml

# DORA metrics scorecard
pptgen example copy devops_metrics --output workspace/decks/devops_metrics.yaml

# Executive update
pptgen example copy executive_update --output workspace/decks/executive_update.yaml
```

---

## Gaps

No known gaps. All patterns referenced in playbooks now have example files.
