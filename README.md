# pptgen

### Template-Driven PowerPoint Generation Platform

![CI](https://img.shields.io/badge/build-passing-brightgreen)\
![Python](https://img.shields.io/badge/python-3.10+-blue)\
![Status](https://img.shields.io/badge/status-internal--platform-purple)

`pptgen` is an internal platform for **generating PowerPoint
presentations from structured content and standardized templates**.

Instead of manually building slides, teams define presentation content
in **YAML or JSON**, and `pptgen` produces the final PowerPoint using
approved templates.

This enables:

-   consistent presentation formatting\
-   repeatable reporting workflows\
-   easier collaboration across teams\
-   automation of presentation artifacts

The platform is designed for **team-scale usage** with templates stored
in **OneDrive / SharePoint** and source code managed through **GitHub**.

------------------------------------------------------------------------

# Table of Contents

-   [Why pptgen?](#why-pptgen)
-   [Key Features](#key-features)
-   [Requirements](#requirements)
-   [Quick Start](#quick-start)
-   [Example Output](#example-output)
-   [Supported Slide Types](#supported-slide-types)
-   [Architecture Overview](#architecture-overview)
-   [Project Structure](#project-structure)
-   [Templates](#templates)
-   [Template Lifecycle](#template-lifecycle)
-   [CLI Commands](#cli-commands)
-   [Testing](#testing)
-   [Security Considerations](#security-considerations)
-   [Troubleshooting](#troubleshooting)
-   [Documentation](#documentation)
-   [Contributing](#contributing)
-   [Release Process](#release-process)
-   [Long-Term Vision](#long-term-vision)

------------------------------------------------------------------------

# Why pptgen?

Many teams repeatedly build similar presentations such as:

-   leadership updates\
-   operational reviews\
-   architecture presentations\
-   project status updates\
-   KPI dashboards

These decks are typically recreated manually each reporting cycle.

`pptgen` transforms this process into a **structured pipeline**:

YAML Content → Template Validation → PowerPoint Rendering → Final
Presentation (.pptx)

For example, a **weekly operations report** can be generated from a YAML
definition and an approved template rather than manually rebuilding
slides.

This results in a **repeatable presentation artifact pipeline**.

------------------------------------------------------------------------

# Key Features

### Template-Driven Slides

Presentations are generated from **approved PowerPoint templates**.

### Structured Content Inputs

Slides are defined using **YAML or JSON**.

### CLI Generation Tool

Create decks with a simple command:

    pptgen build

### Template Registry

All templates are centrally registered and versioned.

### Enterprise Storage Integration

Templates can be stored in **OneDrive or SharePoint**.

### Validation and CI Support

The platform validates templates, content, and slide compatibility.

------------------------------------------------------------------------

# Requirements

Minimum requirements:

-   **Python 3.10+**
-   Access to approved **PowerPoint templates (.pptx)**
-   Access to template storage via **OneDrive or SharePoint**
-   Git (for repository cloning)

------------------------------------------------------------------------

# Quick Start

## 1. Clone the Repository

    git clone https://github.com/<org>/pptgen.git
    cd pptgen

## 2. Install the Package

    pip install -e .

## 3. Create a Deck Definition

Example `deck.yaml`:

``` yaml
deck:
  title: DevOps Strategy
  author: David Harris
  template: ops_review_v1

slides:

  - type: title
    title: DevOps Transformation
    subtitle: 30-60-90 Day Plan

  - type: bullets
    title: Strategic Priorities
    bullets:
      - Stabilize production pipelines
      - Improve deployment consistency
      - Implement observability standards
```

## 4. Generate the Presentation

    pptgen build   --template ops_review_v1   --input deck.yaml   --output devops_strategy.pptx

This command generates **`devops_strategy.pptx`** in the current
directory using the selected template.

------------------------------------------------------------------------

# Example Output

A generated deck may contain slides such as:

Title Slide\
DevOps Transformation\
30-60-90 Day Plan

Bullet Slide\
Strategic Priorities\
• Stabilize production pipelines\
• Improve deployment consistency\
• Implement observability standards

------------------------------------------------------------------------

# Supported Slide Types

    title
    section
    bullets
    two_column
    metric_summary
    image_caption

------------------------------------------------------------------------

# Architecture Overview

Content Input (YAML / JSON)\
→ Schema Validation\
→ Template Registry\
→ Template Loader\
→ Template Inspector\
→ Rendering Engine\
→ PowerPoint Output (.pptx)

------------------------------------------------------------------------

# Project Structure

    pptgen/

    README.md
    CHANGELOG.md
    pyproject.toml

    src/
     └── pptgen/
          ├── cli.py
          ├── engine/
          ├── models/
          ├── registry/
          ├── connectors/
          └── utils/

    templates/
    examples/
    tests/
    docs/
    .github/

------------------------------------------------------------------------

# Templates

Templates define the visual layout of generated presentations.

Each template must include:

-   defined slide layouts\
-   supported placeholders\
-   template metadata\
-   template ownership

All templates must be registered in:

    templates/registry.yaml

------------------------------------------------------------------------

# Template Lifecycle

Draft → Review → Approved → Deprecated → Archived

Only **Approved templates** may be used for production deck generation.

------------------------------------------------------------------------

# CLI Commands

Build presentation

    pptgen build

Validate deck

    pptgen validate --input deck.yaml

List templates

    pptgen list-templates

Inspect template

    pptgen inspect-template

------------------------------------------------------------------------

# Testing

Run tests:

    pytest

Tests include:

-   unit tests
-   integration tests
-   snapshot tests

------------------------------------------------------------------------

# Security Considerations

-   no secrets stored in configuration files
-   generated presentations must **never overwrite templates**
-   SharePoint access uses existing user permissions

------------------------------------------------------------------------

# Troubleshooting

Template Not Found → ensure template exists in `templates/registry.yaml`

Unsupported Slide Type → verify supported slide list

Missing Placeholder → confirm placeholder exists in template

------------------------------------------------------------------------

# Documentation

See `/docs` directory for full documentation.

------------------------------------------------------------------------

# Contributing

Contributions via pull requests.

Requirements:

-   templates must pass validation
-   new features require tests
-   documentation updates required

------------------------------------------------------------------------

# Release Process

Releases occur **monthly or as needed**.

All releases must update:

    CHANGELOG.md

------------------------------------------------------------------------

# Long-Term Vision

The platform may evolve into a **presentation automation system**
capable of generating:

-   executive reporting decks
-   architecture slide packs
-   dashboard-to-slide reporting
-   operational briefings
