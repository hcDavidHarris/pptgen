# Template Validation Checklist

### pptgen Template Submission Checklist

Version: 1.1\
Owner: Analytics / DevOps Platform Team

------------------------------------------------------------------------

# Purpose

This checklist ensures PowerPoint templates are **compatible with the
pptgen rendering engine** before they are submitted for approval.

Completing this checklist prevents the most common template failures:

-   missing placeholders
-   layout mismatches
-   unsupported formatting
-   invalid template structure

This checklist should be completed **before submitting a template pull
request**.

For full template rules, see:

docs/template-authoring-standard.md

------------------------------------------------------------------------

# Template Designer Workflow

Typical workflow for creating a template:

1.  Start from an approved template
2.  Modify layouts
3.  Add required placeholders
4.  Create manifest.yaml
5.  Run validation script
6.  Submit pull request

------------------------------------------------------------------------

# Before You Start

Before creating a new template confirm:

☐ Start from an approved template whenever possible\
☐ Do not modify slide master structure unnecessarily\
☐ Use approved fonts\
☐ Confirm the template supports required slide types

------------------------------------------------------------------------

# Quick Validation Checklist

Before submitting a template verify:

☐ Template saved as .pptx\
☐ Template folder created under templates/\
☐ manifest.yaml created\
☐ template_id matches folder name\
☐ Each slide type maps to exactly one layout\
☐ Layout names follow naming convention\
☐ Required placeholders exist\
☐ Placeholder names follow naming rules\
☐ Placeholder text fields are empty\
☐ No hidden shapes or text\
☐ No manually drawn bullet characters\
☐ No custom fonts requiring installation\
☐ Validation script passes

------------------------------------------------------------------------

# Detailed Validation Checklist

## 1. Template File

☐ File format is .pptx\
☐ Template opens without warnings\
☐ Slide master layouts exist\
☐ Template file size is reasonable (\<20MB recommended)

------------------------------------------------------------------------

## 2. Layout Validation

Layout naming convention:

`<SlideType> Layout`

Examples:

-   Title Layout\
-   Bullets Layout\
-   Two Column Layout\
-   Metric Summary Layout\
-   Image Caption Layout

Checklist:

☐ Layout names follow naming convention\
☐ Layout names are unique\
☐ Each slide type has exactly one layout\
☐ No layouts represent multiple slide types

------------------------------------------------------------------------

## 3. Placeholder Validation

Example placeholders:

Title Slide\
TITLE\
SUBTITLE

Bullet Slide\
TITLE\
BULLETS

Two Column Slide\
TITLE\
LEFT_CONTENT\
RIGHT_CONTENT

Checklist:

☐ All required placeholders exist\
☐ Placeholder names follow UPPERCASE_SNAKE_CASE\
☐ Placeholder names are descriptive\
☐ Placeholder names are not duplicated\
☐ Placeholder text fields are empty\
☐ No ambiguous names (TextBox1, ContentBox, etc.)

------------------------------------------------------------------------

## 4. Layout Design Validation

☐ Each layout represents a single slide type\
☐ Layout margins are consistent\
☐ Placeholders do not overlap\
☐ No invisible placeholders\
☐ No content outside slide boundaries

Example layout:

+--------------------------------+
| ## TITLE                       |
|                                |
| • bullet 1 • bullet 2 • bullet |
| 3                              |
+--------------------------------+

------------------------------------------------------------------------

## 5. Fonts and Branding

☐ Fonts are standard (Calibri, Arial, Segoe UI)\
☐ No custom fonts required\
☐ Branding implemented through slide master\
☐ Theme colors applied consistently

------------------------------------------------------------------------

## 6. Forbidden Template Patterns

☐ Manual bullet symbols\
☐ Hidden shapes\
☐ Hidden text\
☐ Dynamic formatting\
☐ Multiple layouts for the same slide type\
☐ Custom fonts requiring installation

------------------------------------------------------------------------

## 7. Template Manifest Validation

Example manifest:

``` yaml
template_id: ops_review_v1
version: 1.0

owner: Analytics Services
backup_owner: DevOps Platform Team

status: draft

supported_slide_types:
  - title
  - bullets
  - two_column
  - metric_summary
```

Checklist:

☐ template_id defined\
☐ template_id matches template folder name\
☐ version defined\
☐ owner defined\
☐ backup_owner defined\
☐ supported_slide_types defined

------------------------------------------------------------------------

## 8. Repository Structure

Example structure:

templates/

ops_review_v1/\
template.pptx\
manifest.yaml

Checklist:

☐ Template stored in correct folder\
☐ Folder name matches template_id\
☐ manifest.yaml included

------------------------------------------------------------------------

## 9. Run Template Validation Script

Example command:

`pptgen validate-template templates/ops_review_v1`

Expected result:

Validation completed successfully\
No errors\
No warnings

Checklist:

☐ Validation script runs successfully\
☐ No validation errors reported\
☐ No validation warnings reported

------------------------------------------------------------------------

# Submit Template for Review

1.  Commit template.pptx\
2.  Commit manifest.yaml\
3.  Update template registry if required\
4.  Submit pull request

Platform maintainers will review the template.

------------------------------------------------------------------------

# Final Pre‑Submission Check

☐ Template follows Template Authoring Standard\
☐ All required placeholders exist\
☐ Layout naming rules followed\
☐ Validation script passes\
☐ Manifest metadata complete

Once approved the template will move to **Approved** status and become
available for use in pptgen.

------------------------------------------------------------------------

# Common Causes of Template Rejection

Missing placeholders\
Incorrect layout names\
Custom fonts\
Hidden shapes\
Manual bullet characters\
Missing manifest file\
Duplicate placeholders

------------------------------------------------------------------------

# Summary

The Template Validation Checklist ensures templates:

-   follow platform standards
-   render reliably
-   integrate with the pptgen engine

Completing this checklist significantly reduces template-related
failures.
