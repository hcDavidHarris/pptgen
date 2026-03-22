# Playbook Example: ADO Sprint Summary → Weekly Delivery Deck

This example demonstrates the `ado_summary_to_weekly_delivery` playbook route end to end.

---

## Raw Input

The following is a representative sprint summary derived from an Azure DevOps query export:

```
Sprint 24 Summary — Platform Engineering Team
Sprint dates: March 10 – March 21, 2026

Completed:
- pptgen CLI scaffold command (Story #1042) — DONE
- Template placeholder idx mapping fix (Bug #1051) — DONE
- Authoring contract documentation (Story #1038) — DONE
- JSON schema draft for deck validation (Story #1044) — DONE

In Progress:
- CLI workspace init command (Story #1048) — 60% complete
- Example library: architecture patterns (Story #1053) — 40% complete

Blockers:
- Template .potx file not committed to repo — blocking image_caption render tests
- ADO integration spike not yet scoped — no owner assigned

Metrics:
- Stories completed: 4
- Stories in progress: 2
- Story points completed: 21
- Story points committed: 34
- Completion rate: 62%

Notes: Strong delivery on authoring contract work. Template file gap is the primary risk for next sprint.
```

---

## Routing Decision

**Input type:** `ado_export_summary`, `sprint_summary`
**Matched route:** `ado_summary_to_weekly_delivery`
**Playbook:** `docs/ai-playbooks/ado-summary-to-weekly-delivery.md`
**Example pattern:** `examples/engineering_delivery/weekly_delivery_update.yaml`
**Output target:** `workspace/decks/weekly_delivery_update.yaml`

---

## Reasoning

1. Input is an ADO sprint summary — direct match to the `ado_summary_to_weekly_delivery` route.
2. Completed items → bullets slide (highlights).
3. In-progress items → bullets slide (in progress).
4. Blockers → bullets slide.
5. Metrics (stories completed, points, completion rate) → `metric_summary` slide with 4 metrics.
6. Notes can be omitted from the slide deck or absorbed into bullets.
7. Template defaults to `ops_review_v1`.
8. Section slides used to separate highlights, risks, and metrics.

---

## Resulting YAML Deck

```yaml
deck:
  title: Weekly Engineering Delivery Update
  template: ops_review_v1
  author: Platform Engineering
  version: "1.0"
  date: 2026-03-22
  status: draft

slides:
  - type: title
    id: title_slide
    title: Weekly Engineering Delivery Update
    subtitle: Platform Team — Sprint 24

  - type: section
    id: highlights_section
    section_title: Sprint 24 Highlights

  - type: bullets
    id: completed
    title: Completed This Sprint
    bullets:
      - CLI scaffold command delivered (Story #1042)
      - Template placeholder idx mapping fixed (Bug #1051)
      - Authoring contract documentation complete (Story #1038)
      - JSON schema draft for deck validation (Story #1044)

  - type: bullets
    id: in_progress
    title: In Progress
    bullets:
      - CLI workspace init command — 60% complete (Story #1048)
      - Example library — architecture patterns — 40% complete (Story #1053)

  - type: section
    id: blockers_section
    section_title: Risks and Blockers

  - type: bullets
    id: blockers
    title: Active Blockers
    bullets:
      - Template .potx file not committed — blocking image_caption render tests
      - ADO integration spike not yet scoped — no owner assigned

  - type: section
    id: metrics_section
    section_title: Delivery Metrics

  - type: metric_summary
    id: sprint_metrics
    title: Sprint 24 Delivery Metrics
    metrics:
      - label: Stories Completed
        value: "4"
      - label: Stories In Progress
        value: "2"
      - label: Story Points Completed
        value: "21"
      - label: Sprint Completion Rate
        value: "62%"
```

---

## Follow-up Commands

```bash
pptgen validate --input workspace/decks/weekly_delivery_update.yaml
pptgen build --input workspace/decks/weekly_delivery_update.yaml
```

Expected output: `workspace/output/Weekly_Engineering_Delivery_Update.pptx`
