"""Pydantic models for deck-level structure.

Legacy deck YAML has exactly two top-level keys:

    deck:    (DeckMetadata)
    slides:  (list[SlideUnion])

Phase 9 structured deck YAML may additionally include:

    primitive: <id>          — top-level primitive for single-slide decks
    theme:     <id>          — design system theme override
    content:   {…}           — content fields for a top-level primitive
    layout:    <id>          — injected by primitive resolver
    slots:     {…}           — injected by primitive resolver

Any other top-level key is still rejected by extra='forbid'.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .slides import SlideUnion


class DeckMetadata(BaseModel):
    """Metadata block at the top of every deck YAML file.

    Required fields: title, template, author.
    Optional fields: subtitle, version, date, status, description, tags.

    The `version` field is coerced to string because PyYAML parses an
    unquoted ``version: 1.0`` as a float.  A companion warning is emitted
    by the validator layer when this coercion occurs.
    """

    model_config = ConfigDict(extra="forbid")

    # Required
    title: str = Field(min_length=1)
    template: str = Field(min_length=1)
    author: str = Field(min_length=1)

    # Optional
    subtitle: str | None = None
    version: str | None = None
    date: str | None = None
    status: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("version", mode="before")
    @classmethod
    def coerce_version_to_string(cls, v: Any) -> Any:
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


class DeckFile(BaseModel):
    """Top-level model for a complete pptgen deck YAML file.

    Validates that the document has the two required top-level keys
    (``deck`` and ``slides``) and that ``slides`` contains at least one slide.

    Optional Phase 9 fields (``primitive``, ``theme``, ``content``,
    ``layout``, ``slots``) are accepted when present.  All other extra
    top-level keys are still rejected by ``extra='forbid'``.
    """

    model_config = ConfigDict(extra="forbid")

    deck: DeckMetadata
    slides: list[SlideUnion] = Field(min_length=1)

    # Phase 9 structured deck fields (all optional)
    primitive: str | None = None
    theme: str | None = None
    content: dict[str, Any] | None = None
    layout: str | None = None
    slots: dict[str, Any] | None = None
