# Playbook Example: Meeting Notes → EOS Rocks Deck

This example demonstrates the `meeting_notes_to_eos_rocks` playbook route end to end.

---

## Raw Input

The following is a representative set of meeting notes from a quarterly planning session:

```
Q2 Planning Session — March 2026
Attendees: David Harris, Engineering Lead; Alex Chen, Product; Sam Rivera, Operations

Company Rocks (agreed):
- Ship pptgen Phase 3 to all pilot teams by end of quarter
- Achieve 80% reduction in manual deck preparation time
- Complete onboarding documentation and training materials

Engineering Team Rocks:
- Implement CLI workspace init and scaffold commands
- Expand example library to cover architecture and ADR patterns
- Harden schema validation with JSON schema integration

Product Team Rocks:
- Define Phase 4 roadmap based on pilot team feedback
- Publish adoption metrics dashboard

Operations Rocks:
- Establish template governance process
- Document template versioning and deprecation policy

Quarter-end success criteria:
- 5 teams generating decks autonomously
- Zero manual formatting required for weekly reports
- All validation errors self-serviceable via CLI explainer
```

---

## Routing Decision

**Input type:** `meeting_notes`, `quarterly_planning_notes`
**Matched route:** `meeting_notes_to_eos_rocks`
**Playbook:** `docs/ai-playbooks/meeting-notes-to-eos-rocks.md`
**Example pattern:** `examples/eos/eos_rocks.yaml`
**Output target:** `workspace/decks/eos_rocks.yaml`

---

## Reasoning

1. Input contains quarterly planning notes with company-level and functional-team-level priorities — this maps directly to the EOS Rocks structure.
2. "Company Rocks" becomes a section + bullets slide.
3. Engineering, Product, and Operations team rocks are parallel functional priorities — a `two_column` slide works well for functional splits.
4. Success criteria maps to a closing bullets slide.
5. No quantitative KPIs are present, so no `metric_summary` slide is needed.
6. Template defaults to `ops_review_v1`.

---

## Resulting YAML Deck

```yaml
deck:
  title: Q2 EOS Quarterly Rocks
  template: ops_review_v1
  author: David Harris
  version: "1.0"
  date: 2026-03-22
  status: draft

slides:
  - type: title
    id: title_slide
    title: Q2 EOS Quarterly Rocks
    subtitle: Priorities for Q2 2026

  - type: section
    id: company_rocks_section
    section_title: Company Rocks

  - type: bullets
    id: company_rocks
    title: Top Company Rocks
    bullets:
      - Ship pptgen Phase 3 to all pilot teams by end of quarter
      - Achieve 80% reduction in manual deck preparation time
      - Complete onboarding documentation and training materials

  - type: section
    id: team_rocks_section
    section_title: Team Rocks

  - type: two_column
    id: team_rocks
    title: Functional Team Priorities
    left_content:
      - Engineering: CLI workspace init and scaffold commands
      - Engineering: Expand example library to ADR patterns
      - Engineering: Harden schema validation
    right_content:
      - Product: Define Phase 4 roadmap
      - Product: Publish adoption metrics dashboard
      - Operations: Establish template governance process
      - Operations: Document versioning and deprecation policy

  - type: section
    id: success_section
    section_title: Quarter-End Success Criteria

  - type: bullets
    id: success_criteria
    title: Quarter-End Success Criteria
    bullets:
      - 5 teams generating decks autonomously
      - Zero manual formatting required for weekly reports
      - All validation errors self-serviceable via CLI explainer
```

---

## Follow-up Commands

```bash
pptgen validate --input workspace/decks/eos_rocks.yaml
pptgen build --input workspace/decks/eos_rocks.yaml
```

Expected output: `workspace/output/Q2_EOS_Quarterly_Rocks.pptx`
