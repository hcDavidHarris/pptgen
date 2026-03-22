# Playbook: Azure DevOps Summary → Weekly Delivery Deck

## Input

ADO query exports or delivery summaries.

Example sources:

- sprint query export
- feature status report
- backlog summary

## Pattern

Use:

examples/engineering_delivery/weekly_delivery_update.yaml

## Prompt

Convert this Azure DevOps delivery summary into a pptgen YAML deck.

Use examples/engineering_delivery/weekly_delivery_update.yaml as the pattern.

Requirements:

- include title slide
- include weekly highlights
- include blockers
- include delivery metrics

## Output

workspace/decks/weekly_delivery_update.yaml

## Workflow

ADO export → summary → YAML → pptgen build

## Typical Use

Weekly engineering leadership updates.