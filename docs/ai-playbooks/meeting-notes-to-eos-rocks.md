# Playbook: Meeting Notes → EOS Rocks Deck

## Input

Meeting notes or leadership summary.

Example source:

- Zoom meeting summary
- leadership discussion notes
- quarterly planning notes

## Pattern

Use the example:

examples/eos/eos_rocks.yaml

## Prompt

Convert the following meeting notes into a pptgen YAML deck.

Use examples/eos/eos_rocks.yaml as the pattern.

Requirements:

- identify the top 3–5 priorities
- format them as EOS rocks
- keep language concise
- ensure the deck remains leadership friendly

## Output

workspace/decks/eos_rocks.yaml

## Workflow

notes → YAML → pptgen validate → pptgen build

## Typical Use

Quarterly leadership planning.