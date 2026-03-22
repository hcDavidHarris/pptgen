# Playbook: DevOps Metrics → Engineering Scorecard Deck

## Input

DevOps metrics summary.

Example sources:

- monitoring dashboards
- DORA metrics exports
- CI/CD analytics

## Pattern

Use:

examples/devops/devops_metrics.yaml

## Prompt

Convert these DevOps metrics into a pptgen YAML scorecard deck.

Use examples/devops/devops_metrics.yaml as the pattern.

Requirements:

- highlight key DevOps indicators
- include 3–4 metrics
- ensure metrics fit the metric_summary slide

## Output

workspace/decks/devops_metrics.yaml

## Workflow

metrics summary → YAML → pptgen build

## Typical Use

Engineering operational reviews.