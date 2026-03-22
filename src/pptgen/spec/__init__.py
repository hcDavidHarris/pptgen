"""pptgen presentation spec layer.

This package provides the PresentationSpec model and the spec-to-deck
translator.  The spec layer sits above the existing renderer pipeline
and is never imported by it.

Typical usage::

    from pptgen.spec.presentation_spec import PresentationSpec, SectionSpec
    from pptgen.spec.spec_to_deck import convert_spec_to_deck

    spec = PresentationSpec(
        title="Q2 Engineering Update",
        subtitle="Analytics Platform Team",
        sections=[
            SectionSpec(title="Highlights", bullets=["Shipped feature X", "Reduced latency"]),
        ],
    )
    deck_dict = convert_spec_to_deck(spec)
"""
