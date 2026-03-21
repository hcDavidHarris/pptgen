# Template Authoring Standard

### pptgen PowerPoint Template Specification

Version: 1.1\
Owner: Analytics / DevOps Platform Team\
Status: Draft Standard

------------------------------------------------------------------------

# 1. Purpose

This document defines the **rules and standards for creating PowerPoint
templates compatible with the `pptgen` platform**.

The purpose of this standard is to ensure that templates:

-   render reliably
-   behave consistently across teams
-   support automated slide generation
-   remain maintainable as the platform evolves

Templates that do not follow this standard **must not be registered in
the template registry**.

For system architecture details, see:

docs/implementation-plan.md

------------------------------------------------------------------------

# 2. Design Principles

Templates **must follow the principles below**.

## Deterministic Layouts

Each slide type must map to **exactly one slide layout**.

Example mapping:

title → Title Layout\
bullets → Bullets Layout\
two_column → Two Column Layout

Layouts must not change dynamically.

------------------------------------------------------------------------

## Placeholder-Based Content

All content areas must use **PowerPoint placeholders**.

Avoid manually created text boxes whenever possible.

Correct: - Title Placeholder - Content Placeholder

Incorrect: - Custom text boxes drawn manually

------------------------------------------------------------------------

## Minimal Template Logic

Templates must contain **layout and visual style only**.

Business logic belongs in:

-   YAML content
-   pptgen rendering engine

Templates must not rely on:

-   manual formatting tricks
-   layout-dependent logic
-   manual bullet symbols

------------------------------------------------------------------------

## Layout Stability

Once a template is approved:

-   slide layouts must not change
-   placeholder names must remain stable

Breaking layout changes require **a new template version**.

------------------------------------------------------------------------

## Platform Compatibility

Templates must be compatible with:

-   Microsoft PowerPoint 2019
-   Microsoft 365

Templates must be saved as `.pptx`.

------------------------------------------------------------------------

# 3. Template File Requirements

Every template must include the following components.

  Requirement         Description
  ------------------- -------------------------------------------
  File Format         `.pptx`
  Slide Layouts       Layouts defined for supported slide types
  Placeholders        Required placeholders must exist
  Template Manifest   Metadata describing template
  Ownership           Template must define owners

------------------------------------------------------------------------

# 4. Supported Slide Types

Templates must support one or more of the following slide types.

title\
section\
bullets\
two_column\
metric_summary\
image_caption

Each slide type must map to **exactly one PowerPoint layout**.

------------------------------------------------------------------------

# 5. Layout Naming Convention

Layouts must follow the naming pattern:

`<SlideType> Layout`

Examples:

-   Title Layout
-   Bullets Layout
-   Two Column Layout
-   Metric Summary Layout
-   Image Caption Layout

Layout names must be unique.

------------------------------------------------------------------------

# 6. Placeholder Naming Standard

Placeholder names must follow this naming convention.

Naming rules:

-   UPPERCASE
-   SNAKE_CASE
-   DESCRIPTIVE

Examples:

TITLE\
SUBTITLE\
BULLETS\
LEFT_CONTENT\
RIGHT_CONTENT\
IMAGE\
CAPTION\
METRIC_1_VALUE\
METRIC_1_LABEL

Avoid names like:

TextBox1\
MyText\
ContentBox

------------------------------------------------------------------------

# 7. Placeholder Types

Placeholders represent structured content types used by the rendering
engine.

  Type      Description
  --------- -------------------
  TEXT      single text value
  BULLETS   bullet list
  IMAGE     image insertion
  METRIC    numeric metric
  CAPTION   descriptive text
  SECTION   section heading

Example mapping:

BULLETS → BULLETS placeholder\
IMAGE → IMAGE placeholder\
METRIC_1_VALUE → metric value

------------------------------------------------------------------------

# 8. Required Placeholders by Slide Type

## Title Slide

Required placeholders:

TITLE\
SUBTITLE

------------------------------------------------------------------------

## Section Slide

Required placeholders:

SECTION_TITLE

Optional:

SECTION_SUBTITLE

------------------------------------------------------------------------

## Bullet Slide

Required placeholders:

TITLE\
BULLETS

------------------------------------------------------------------------

## Two Column Slide

Required placeholders:

TITLE\
LEFT_CONTENT\
RIGHT_CONTENT

------------------------------------------------------------------------

## Metric Summary Slide

Required placeholders:

TITLE\
METRIC_1_VALUE\
METRIC_1_LABEL\
METRIC_2_VALUE\
METRIC_2_LABEL

------------------------------------------------------------------------

## Image Caption Slide

Required placeholders:

TITLE\
IMAGE\
CAPTION

------------------------------------------------------------------------

# 9. Layout Design Requirements

## One Slide Type per Layout

Each layout must represent **a single logical slide type**.

------------------------------------------------------------------------

## No Hidden Content

Templates must not include:

-   hidden shapes
-   hidden text
-   invisible placeholders

------------------------------------------------------------------------

## No Dynamic Formatting

Avoid:

-   auto-resizing text logic
-   manually styled bullet characters
-   layout-dependent formatting

------------------------------------------------------------------------

## Consistent Margins

Recommended margins:

Top: 1.0 in\
Bottom: 1.0 in\
Left: 1.0 in\
Right: 1.0 in

------------------------------------------------------------------------

# 10. Fonts and Branding

Templates should use **standard fonts available across the
organization**.

Recommended fonts:

Calibri\
Arial\
Segoe UI

Avoid custom fonts requiring installation.

Branding should be implemented through:

-   slide master
-   background graphics
-   theme colors

------------------------------------------------------------------------

# 11. Template Manifest

Each template must include a **template manifest file**.

Example:

``` yaml
template_id: ops_review_v1
version: 1.0

owner: Analytics Services
backup_owner: DevOps Platform Team

status: approved

supported_slide_types:
  - title
  - bullets
  - two_column
  - metric_summary
```

------------------------------------------------------------------------

# 12. Template Validation Rules

Templates must pass the following validation checks:

-   required layouts exist
-   layout names follow naming convention
-   required placeholders exist
-   placeholder names follow standard
-   slide types map correctly to layouts
-   template manifest exists

Templates failing validation **cannot be approved**.

------------------------------------------------------------------------

# 13. Template Creation Workflow

1.  Duplicate an approved template
2.  Modify layouts
3.  Add required placeholders
4.  Create manifest.yaml
5.  Run template validation tool
6.  Submit pull request
7.  Platform team review
8.  Template registered

------------------------------------------------------------------------

# 14. Template Lifecycle

Draft\
Review\
Approved\
Deprecated\
Archived

Only **Approved templates** may be used for production generation.

------------------------------------------------------------------------

# 15. Template Versioning

Breaking layout changes require a **new template version**.

Example:

ops_review_v1\
ops_review_v2\
ops_review_v3

------------------------------------------------------------------------

# 16. Template Ownership

Each template must define:

primary_owner\
backup_owner

Owners are responsible for:

-   maintaining template quality
-   placeholder stability
-   responding to issues

------------------------------------------------------------------------

# 17. Forbidden Template Patterns

Templates must not include:

-   manual bullet characters
-   multiple layouts for one slide type
-   unlabeled placeholders
-   custom fonts requiring installation
-   hidden shapes or text
-   dynamic formatting tricks

------------------------------------------------------------------------

# 18. Example Template Structure

templates/

ops_review_v1/ template.pptx manifest.yaml

------------------------------------------------------------------------

# 19. Template Approval Process

1.  Create template
2.  Add manifest
3.  Run validation
4.  Submit pull request
5.  Platform team review
6.  Template registered

------------------------------------------------------------------------

# 20. Future Enhancements

Potential future features:

-   chart placeholders
-   table data injection
-   layout metadata tagging
-   automated template validation tools

------------------------------------------------------------------------

# Final Note

The Template Authoring Standard defines the **contract between
PowerPoint templates and the pptgen rendering engine**.

Following this standard ensures presentations can be generated
**reliably, consistently, and at scale** across teams.
