
# Contributing to pptgen

Thank you for contributing to **pptgen**, a template-driven platform for generating PowerPoint presentations from structured YAML.

This document explains how to contribute improvements to:

- documentation
- templates
- example decks
- Claude skills
- platform code

Following these guidelines helps keep the platform **consistent, maintainable, and easy for teams to adopt**.

---

# Contribution Types

| Contribution | Description |
|---|---|
| Documentation | Improvements to guides or standards |
| Example Decks | New YAML examples demonstrating use cases |
| Templates | New PowerPoint templates |
| Claude Skills | Improvements to AI authoring capabilities |
| Platform Code | Enhancements to the pptgen rendering engine |

---

# Repository Structure

```
pptgen/
│
├─ README.md
├─ CONTRIBUTING.md
│
├─ docs/
│
├─ skills/
│
├─ examples/
│
├─ templates/
│
└─ pptgen/
```

Each folder has a specific responsibility.

---

# Development Workflow

### 1. Create a Branch

Never commit directly to `main`.

```
git checkout -b feature/my-change
```

Examples:

```
git checkout -b docs/update-authoring-guide
git checkout -b template/new-executive-template
git checkout -b skill/improve-yaml-validation
```

---

### 2. Make Your Changes

Modify or add files in the appropriate directories.

Examples:

- `docs/` for documentation
- `templates/` for PowerPoint templates
- `examples/` for YAML deck examples
- `skills/` for Claude skill definitions

---

### 3. Validate Your Changes

Before committing, verify that:

- documentation renders correctly
- YAML examples follow the schema
- templates support required slide types
- Claude skills follow naming conventions

---

### 4. Commit Changes

Use clear commit messages.

Example:

```
git commit -m "Add example architecture deck"
```

Good commit messages:

- Add KPI dashboard example deck
- Improve deck authoring guide
- Add validation rule for metric slides
- Add architecture_overview_v1 template

---

### 5. Push Your Branch

```
git push origin feature/my-change
```

---

### 6. Create a Pull Request

Open a pull request in GitHub and include:

- description of the change
- reason for the change
- screenshots or examples if relevant

---

# Contributing Documentation

Documentation is stored in:

```
docs/
```

Documentation should:

- be written in Markdown
- include examples when possible
- link to related documents

---

# Contributing Example Decks

Example decks are located in:

```
examples/
```

Examples should:

- demonstrate real use cases
- be simple and readable
- follow the YAML schema
- pass validation

Example categories:

- executive updates
- architecture reviews
- operational reports
- KPI dashboards
- strategy presentations

---

# Contributing Templates

Templates are stored in:

```
templates/
```

Templates must support these slide types:

- title
- section
- bullets
- two_column
- metric_summary
- image_caption

Naming convention:

```
<template_name>_v<version>.pptx
```

Example:

```
executive_brief_v1.pptx
ops_review_v1.pptx
architecture_overview_v1.pptx
```

---

# Contributing Claude Skills

Claude skills are located in:

```
skills/
```

Current skills include:

- generate_pptgen_deck_yaml
- validate_pptgen_deck_yaml
- improve_pptgen_deck_yaml

Skills should:

- follow naming conventions
- define clear inputs and outputs
- maintain compatibility with the YAML schema

---

# Code Contributions

If contributing to the rendering engine:

```
pptgen/
```

Code changes should:

- maintain YAML compatibility
- support existing templates
- include clear documentation
- avoid breaking changes when possible

---

# Reporting Issues

If you discover issues with:

- templates
- YAML schema
- example decks
- documentation

Open a GitHub issue and include:

- description of the problem
- steps to reproduce
- example YAML if applicable

---

# Summary

pptgen is designed as a **structured presentation generation platform**.

Contributions help improve:

- documentation
- templates
- examples
- AI workflows
- rendering capabilities

Following these guidelines ensures the platform remains **consistent, scalable, and easy for teams to adopt**.
