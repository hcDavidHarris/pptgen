# Presentation Spec Layer

Version: 1.0
Owner: Analytics / DevOps Platform Team

---

## Purpose

The presentation spec layer separates **semantic content** from **slide layout**.

In the existing pipeline, authors (human or AI) write deck YAML directly —
specifying slide types, field names, and content in one step.  This works well
for deterministic templates but requires detailed knowledge of the slide type
contract.

The spec layer introduces a higher-level vocabulary:

```
PresentationSpec  →  spec_to_deck()  →  deck YAML  →  pptgen validate/build  →  .pptx
```

Authors describe **what they want to communicate**; the translator decides
which slide types to use and how to arrange them.

---

## Where It Lives

```
src/pptgen/spec/
  __init__.py              Package entry point
  presentation_spec.py     PresentationSpec, SectionSpec, MetricSpec, ImageSpec
  spec_to_deck.py          convert_spec_to_deck() translator
```

This package has **no dependency on the renderer or template layer**.  It sits
entirely above the existing pipeline and calls into it only through the
standard `load_deck()` / `validate_deck()` / `render_deck()` interface.

---

## Spec Model Hierarchy

```
PresentationSpec
  title            str          Presentation title
  subtitle         str          Subtitle or context line
  author           str          Author name (default: "Unknown")
  template         str          pptgen template ID (default: "ops_review_v1")
  sections[]       SectionSpec

SectionSpec
  title            str          Section heading
  bullets[]        list[str]    Bullet points (max 6 per generated slide)
  metrics[]        MetricSpec   KPI values (max 4 per generated metric_summary slide)
  images[]         ImageSpec    Diagrams / screenshots (one slide each)
  include_section_divider bool  Emit section divider before content (default: True)

MetricSpec
  label            str          Short metric name
  value            str          Metric value as string
  unit             str | None   Optional unit suffix

ImageSpec
  path             str          Image file path (PNG or JPEG)
  caption          str          Explanatory text
  title            str | None   Override for slide title (defaults to section title)
```

All models use `extra='forbid'` — unknown fields are a hard error.

---

## How Specs Map to Deck YAML

The translator (`convert_spec_to_deck`) applies these rules in order:

| Spec content | Generated slide type | Notes |
|---|---|---|
| `PresentationSpec.title` + `subtitle` | `title` | Always the first slide |
| `SectionSpec` (if `include_section_divider=True`) | `section` | One per section |
| `SectionSpec.bullets` | `bullets` | Split into groups of 6 if needed |
| `SectionSpec.metrics` | `metric_summary` | Split into groups of 4 if needed |
| `SectionSpec.images[]` | `image_caption` | One slide per image |

Sections with no content (no bullets, metrics, or images) still emit the
section divider so the deck has structural placeholders.

---

## Usage Example

```python
from pptgen.spec.presentation_spec import (
    PresentationSpec,
    SectionSpec,
    MetricSpec,
    ImageSpec,
)
from pptgen.spec.spec_to_deck import convert_spec_to_deck

spec = PresentationSpec(
    title="Q2 Engineering Update",
    subtitle="Analytics Platform Team",
    author="David Harris",
    template="ops_review_v1",
    sections=[
        SectionSpec(
            title="Delivery Highlights",
            bullets=[
                "Shipped pptgen v1.0 with 6 slide types",
                "Reduced slide creation time by 80%",
                "Onboarded 4 teams in Q2",
            ],
        ),
        SectionSpec(
            title="Platform Metrics",
            metrics=[
                MetricSpec(label="Decks Generated", value="47"),
                MetricSpec(label="Avg Build Time", value="3", unit=" sec"),
                MetricSpec(label="Validation Pass Rate", value="98", unit="%"),
            ],
        ),
        SectionSpec(
            title="Architecture",
            images=[
                ImageSpec(
                    path="assets/pptgen_architecture.png",
                    caption="pptgen pipeline: YAML → validate → render → .pptx",
                ),
            ],
        ),
    ],
)

deck_dict = convert_spec_to_deck(spec)
```

The resulting `deck_dict` can be:

```python
import yaml

# Write to file and validate/build via CLI
with open("workspace/decks/q2_update.yaml", "w") as f:
    yaml.dump(deck_dict, f, allow_unicode=True, sort_keys=False)
```

```bash
pptgen validate --input workspace/decks/q2_update.yaml
pptgen build    --input workspace/decks/q2_update.yaml
```

---

## Future Extensibility

The spec layer is designed for future AI workflows where a model generates a
`PresentationSpec` (high-level semantic intent) rather than a full deck YAML
(layout-specific structure).

Potential extensions:

- **`narrative` field on SectionSpec** — a free-text summary that AI can use
  to derive bullets automatically.
- **`audience` field on PresentationSpec** — drives different template
  selection or bullet density.
- **`SpecRouter`** — a class that takes a spec and a routing table and selects
  the optimal template and slide sequence.
- **`spec_from_notes()`** — an AI-powered function that converts meeting notes
  or ADO exports directly into a `PresentationSpec`.

These extensions can be added to `src/pptgen/spec/` without touching the
renderer pipeline.

---

## Authority

The spec layer is **not** the source of truth for slide type contracts or
template placeholder names.  Those remain in:

- `src/pptgen/slide_registry.py` — slide type metadata
- `src/pptgen/models/slides.py` — Pydantic schema enforcement
- `docs/architecture/authority_map.md` — full source-of-truth table

The spec layer depends on the deck YAML schema being stable; breaking changes
to the deck schema will require corresponding updates to `spec_to_deck.py`.
