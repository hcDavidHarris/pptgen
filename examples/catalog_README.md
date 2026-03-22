# Example Deck Catalog

This catalog provides a machine-friendly and human-friendly index of the example deck libraries in the repo.

Recommended repo locations:

```text
pptgen/
└─ examples/
   ├─ catalog.yaml
   └─ README.md
```

## Libraries

- `eos` — EOS leadership and operating cadence artifacts
- `devops` — DevOps Handbook inspired engineering delivery decks
- `team_topologies` — Team Topologies inspired org and platform team decks
- `architecture` — Architecture review and ADR decks

## Why this catalog exists

It helps:

- humans quickly discover examples
- AI tools select the right example pattern
- future CLI commands list example decks by category
- contributors understand where new examples belong

## Suggested future uses

Potential future CLI support:

```text
pptgen list-examples
pptgen show-example eos_scorecard
pptgen copy-example architecture_review
```

Potential future AI support:

- recommend the right example deck for a use case
- generate new decks based on the closest example
- validate whether a new example belongs in the right library

See `catalog.yaml` for the authoritative inventory.
