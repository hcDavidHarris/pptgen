"""Tests for brief_types: factory functions and dispatch map."""

import pytest

from pptgen.ingestion.brief_types import (
    BRIEF_TYPE_ARCHITECTURE,
    BRIEF_TYPE_DELIVERY,
    BRIEF_TYPE_EOS_ROCKS,
    BRIEF_TYPE_STRATEGIC,
    VALID_BRIEF_TYPES,
    ArchitectureBrief,
    DeliveryBrief,
    EOSRocksBrief,
    StrategicBrief,
    get_brief_factory,
)
from pptgen.ingestion.ingestion_models import BaseBrief


# ---------------------------------------------------------------------------
# Type constants
# ---------------------------------------------------------------------------


class TestTypeConstants:
    def test_valid_brief_types_contains_all_four(self):
        assert VALID_BRIEF_TYPES == frozenset(
            {"strategic", "delivery", "architecture", "eos_rocks"}
        )

    def test_constants_match_valid_set(self):
        assert BRIEF_TYPE_STRATEGIC in VALID_BRIEF_TYPES
        assert BRIEF_TYPE_DELIVERY in VALID_BRIEF_TYPES
        assert BRIEF_TYPE_ARCHITECTURE in VALID_BRIEF_TYPES
        assert BRIEF_TYPE_EOS_ROCKS in VALID_BRIEF_TYPES


# ---------------------------------------------------------------------------
# StrategicBrief factory
# ---------------------------------------------------------------------------


class TestStrategicBrief:
    def test_returns_base_brief(self):
        brief = StrategicBrief(topic="Q1 Vision")
        assert isinstance(brief, BaseBrief)

    def test_brief_type_is_strategic(self):
        brief = StrategicBrief(topic="T")
        assert brief.brief_type == "strategic"

    def test_defaults(self):
        brief = StrategicBrief(topic="My Topic")
        assert brief.topic == "My Topic"
        assert brief.audience == "Executive leadership"
        assert "strategic" in brief.goal.lower() or "align" in brief.goal.lower()
        assert brief.sections == []
        assert brief.provenance == []
        assert brief.confidence is None

    def test_overrides(self):
        brief = StrategicBrief(
            topic="T",
            goal="Custom goal",
            audience="Board",
            sections=[{"title": "S"}],
            confidence=0.9,
        )
        assert brief.goal == "Custom goal"
        assert brief.audience == "Board"
        assert len(brief.sections) == 1
        assert brief.confidence == 0.9


# ---------------------------------------------------------------------------
# DeliveryBrief factory
# ---------------------------------------------------------------------------


class TestDeliveryBrief:
    def test_brief_type(self):
        assert DeliveryBrief(topic="T").brief_type == "delivery"

    def test_default_audience(self):
        brief = DeliveryBrief(topic="Sprint 5")
        assert "engineering" in brief.audience.lower() or "product" in brief.audience.lower()

    def test_returns_base_brief(self):
        assert isinstance(DeliveryBrief(topic="T"), BaseBrief)


# ---------------------------------------------------------------------------
# ArchitectureBrief factory
# ---------------------------------------------------------------------------


class TestArchitectureBrief:
    def test_brief_type(self):
        assert ArchitectureBrief(topic="T").brief_type == "architecture"

    def test_default_audience_includes_engineering(self):
        brief = ArchitectureBrief(topic="T")
        assert "engineering" in brief.audience.lower()

    def test_returns_base_brief(self):
        assert isinstance(ArchitectureBrief(topic="T"), BaseBrief)


# ---------------------------------------------------------------------------
# EOSRocksBrief factory
# ---------------------------------------------------------------------------


class TestEOSRocksBrief:
    def test_brief_type(self):
        assert EOSRocksBrief(topic="T").brief_type == "eos_rocks"

    def test_default_goal_mentions_rocks(self):
        brief = EOSRocksBrief(topic="T")
        assert "rock" in brief.goal.lower()

    def test_returns_base_brief(self):
        assert isinstance(EOSRocksBrief(topic="T"), BaseBrief)


# ---------------------------------------------------------------------------
# get_brief_factory dispatch
# ---------------------------------------------------------------------------


class TestGetBriefFactory:
    def test_transcript_maps_to_strategic(self):
        factory = get_brief_factory("transcript")
        assert factory("T").brief_type == BRIEF_TYPE_STRATEGIC

    def test_ado_board_maps_to_delivery(self):
        factory = get_brief_factory("ado_board")
        assert factory("T").brief_type == BRIEF_TYPE_DELIVERY

    def test_ado_repo_maps_to_architecture(self):
        factory = get_brief_factory("ado_repo")
        assert factory("T").brief_type == BRIEF_TYPE_ARCHITECTURE

    def test_eos_maps_to_eos_rocks(self):
        factory = get_brief_factory("eos")
        assert factory("T").brief_type == BRIEF_TYPE_EOS_ROCKS

    def test_unknown_falls_back_to_strategic(self):
        factory = get_brief_factory("unknown_source_type")
        assert factory("T").brief_type == BRIEF_TYPE_STRATEGIC
