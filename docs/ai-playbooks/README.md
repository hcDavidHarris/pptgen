# AI Playbooks

This directory provides the **canonical prompt-and-pattern index** for using AI tools (Claude, ChatGPT, Copilot) with the pptgen platform.

These playbooks connect real-world engineering inputs to pptgen YAML deck generation by defining:

- input type
- example pattern
- prompt structure
- output target

The goal is to make AI-assisted deck creation **repeatable and predictable** for engineering teams.

---

# Purpose

Claude performs best when workflows are explicit and named.

Instead of inferring how to convert raw inputs into decks, playbooks define the correct path.

Examples:

- meeting notes → EOS rocks deck
- Azure DevOps summary → weekly delivery deck
- architecture notes → ADR review deck
- DevOps metrics → engineering scorecard

Each playbook provides:

- recommended prompt
- example YAML pattern
- expected output location

---

# Available Playbooks

| Playbook | Input | Example Pattern | Output |
|---|---|---|---|
| meeting-notes-to-eos-rocks | meeting notes | examples/eos/eos_rocks.yaml | workspace/decks/eos_rocks.yaml |
| ado-summary-to-weekly-delivery | ADO export summary | examples/engineering_delivery/weekly_delivery_update.yaml | workspace/decks/weekly_delivery_update.yaml |
| architecture-notes-to-adr-deck | architecture notes | examples/architecture/adr_review.yaml | workspace/decks/adr_review.yaml |
| devops-metrics-to-scorecard | DevOps metrics | examples/devops/devops_metrics.yaml | workspace/decks/devops_metrics.yaml |

---

# Standard Workflow

Most playbooks follow the same pattern:

raw input  
→ AI summarizes content  
→ AI generates YAML using example pattern  
→ pptgen validates YAML  
→ pptgen builds PowerPoint  

---

# Standard Prompt Structure

All playbooks follow this structure:

1. Identify the input type
2. Reference the example YAML deck
3. Specify the output YAML file
4. Keep the content concise and presentation-ready
5. Ensure pptgen schema compatibility

---

# Why Playbooks Matter

This index improves:

- consistency across teams
- AI output quality
- workflow discoverability
- onboarding for new users

It also prepares the platform for future automation such as:

```
pptgen ai generate weekly-delivery
```

where the command simply invokes the correct playbook.