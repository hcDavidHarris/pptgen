# Playbook: Architecture Notes → ADR Review Deck

## Input

Architecture design notes or ADR discussions.

Example sources:

- system design documents
- architecture review notes
- ADR summaries

## Pattern

Use:

examples/architecture/adr_review.yaml

## Prompt

Convert these architecture notes into a pptgen YAML deck.

Use examples/architecture/adr_review.yaml as the pattern.

Requirements:

- summarize the problem statement
- outline architectural options
- highlight the recommended decision
- capture trade-offs

## Output

workspace/decks/adr_review.yaml

## Workflow

architecture notes → YAML → pptgen build

## Typical Use

Architecture review meetings.