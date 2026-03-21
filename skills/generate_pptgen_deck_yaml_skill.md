# Skill: generate_pptgen_deck_yaml

## Purpose

Generate valid `pptgen` deck YAML from presentation ideas, notes,
outlines, meeting summaries, or rough bullet points.

This skill converts unstructured or semi-structured presentation input
into a YAML deck that conforms to the `pptgen` content contract.

The generated YAML must be:

-   valid against the Deck YAML Schema Specification
-   aligned to supported slide types
-   easy for humans to review and edit
-   suitable for rendering by `pptgen`

------------------------------------------------------------------------

## When to Use

Use this skill when the user wants to:

-   create a new `pptgen` deck from notes or ideas
-   convert a presentation outline into YAML
-   turn meeting notes into a slide deck
-   generate a first draft deck for leadership, architecture, KPI, or
    status reporting
-   avoid manually authoring YAML

Do **not** use this skill to validate an existing YAML deck in detail.
That belongs to a validation skill.

------------------------------------------------------------------------

## Inputs

This skill accepts any of the following as input:

-   rough presentation notes
-   section headings
-   bullet points
-   meeting summaries
-   strategy outlines
-   KPI lists
-   architecture summaries
-   explicit requests for specific slide types
-   template name, if provided
-   audience, if provided
-   tone, if provided

The input may be incomplete. Make reasonable, explicit assumptions when
needed.

------------------------------------------------------------------------

## Output

Produce a complete `pptgen` YAML deck.

Output **only the YAML** unless the user explicitly asks for
explanation.

The YAML must contain:

-   a top-level `deck` object
-   a top-level `slides` array
-   valid slide definitions using supported slide types

------------------------------------------------------------------------

## Supported Slide Types

The generated deck may use only these slide types unless the user
explicitly says otherwise and the platform supports more:

-   `title`
-   `section`
-   `bullets`
-   `two_column`
-   `metric_summary`
-   `image_caption`

Do not invent unsupported slide types.

------------------------------------------------------------------------

## Required Deck Structure

Every generated deck must follow this structure:

``` yaml
deck:
  title: <string>
  template: <registered_template_id>
  author: <string>

slides:
  - type: title
    title: <string>
    subtitle: <string>
```

Required deck fields:

-   `deck.title`
-   `deck.template`
-   `deck.author`

If the user does not provide `author`, use a sensible default or the
known user name when available.

If the user does not provide a template, default to:

``` yaml
template: ops_review_v1
```

------------------------------------------------------------------------

## YAML Rules

### Field Naming

Use **lowercase_snake_case** for all YAML keys.

Correct examples:

-   `section_title`
-   `left_content`
-   `image_path`

Incorrect examples:

-   `sectionTitle`
-   `leftContent`
-   `imagePath`

### General Rules

-   Do not use unknown fields
-   Do not output comments inside YAML unless explicitly requested
-   Do not leave required arrays empty
-   Do not emit null for required string fields
-   Keep YAML clean and minimal
-   Preserve logical slide order

Optional fields that may be used when helpful:

-   `id`
-   `notes`
-   `visible`

------------------------------------------------------------------------

## Slide Type Requirements

### Title Slide

``` yaml
- type: title
  title: <string>
  subtitle: <string>
```

Use as the first slide unless instructed otherwise.

------------------------------------------------------------------------

### Section Slide

``` yaml
- type: section
  section_title: <string>
```

Optional:

``` yaml
  section_subtitle: <string>
```

------------------------------------------------------------------------

### Bullet Slide

``` yaml
- type: bullets
  title: <string>
  bullets:
    - <string>
```

Rules:

-   `bullets` must contain at least one item
-   Prefer 3--6 bullets
-   Use concise phrases

------------------------------------------------------------------------

### Two Column Slide

``` yaml
- type: two_column
  title: <string>
  left_content:
    - <string>
  right_content:
    - <string>
```

Use for comparisons such as current vs future state.

------------------------------------------------------------------------

### Metric Summary Slide

``` yaml
- type: metric_summary
  title: <string>
  metrics:
    - label: <string>
      value: <string>
```

Optional metric field:

``` yaml
      unit: <string>
```

Rules:

-   Include at least two metrics
-   Metric values should be strings

------------------------------------------------------------------------

### Image Caption Slide

``` yaml
- type: image_caption
  title: <string>
  image_path: <string>
  caption: <string>
```

Use when diagrams or architecture visuals are referenced.

------------------------------------------------------------------------

## Content Design Guidance

The generated deck should be presentation-friendly.

### Slide Writing Rules

-   keep titles concise
-   keep bullets short and readable
-   prefer phrases over full sentences
-   avoid overcrowding slides
-   organize larger decks into sections
-   use `metric_summary` for KPI-heavy slides
-   use `two_column` for comparisons

------------------------------------------------------------------------

## Deck Composition Defaults

Preferred slide flow:

1.  Title slide
2.  Section slide
3.  Content slides
4.  Additional sections as needed
5.  Metrics or visuals

------------------------------------------------------------------------

## Reasoning Rules

When transforming notes into YAML:

1.  infer logical sections
2.  group related ideas
3.  convert long prose into slide-friendly phrasing
4.  choose the simplest slide type
5.  avoid overengineering the deck
6.  preserve important terminology

------------------------------------------------------------------------

## Template Awareness

If the user specifies a template, use it exactly.

If no template is specified, default to:

``` yaml
template: ops_review_v1
```

------------------------------------------------------------------------

## AI-Assisted Authoring Pattern

Typical workflow:

ideas / notes\
↓\
generate_pptgen_deck_yaml\
↓\
valid pptgen YAML\
↓\
pptgen validate\
↓\
pptgen build

------------------------------------------------------------------------

## Success Criteria

The generated YAML must:

-   follow the pptgen schema
-   use only supported slide types
-   be readable and editable
-   reflect the user's intent
-   be ready for validation and rendering

------------------------------------------------------------------------

## Failure Avoidance

Do not:

-   invent slide types
-   produce malformed YAML
-   use incorrect field names (e.g. `bullet_list`)
-   use camelCase keys
-   create empty arrays
