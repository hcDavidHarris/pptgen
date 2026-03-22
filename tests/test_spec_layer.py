"""Tests for the presentation spec layer.

Covers:
  - PresentationSpec model validation
  - convert_spec_to_deck() translation logic
  - End-to-end: spec → deck dict → load_deck() → validate_deck()
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pptgen.loaders.yaml_loader import load_deck
from pptgen.registry.registry import TemplateRegistry
from pptgen.spec.presentation_spec import (
    ImageSpec,
    MetricSpec,
    PresentationSpec,
    SectionSpec,
)
from pptgen.spec.spec_to_deck import convert_spec_to_deck
from pptgen.validators.deck_validator import validate_deck


_PROJECT_ROOT = Path(__file__).parent.parent
_REGISTRY_PATH = _PROJECT_ROOT / "templates" / "registry.yaml"


@pytest.fixture(scope="module")
def registry() -> TemplateRegistry:
    return TemplateRegistry.from_file(_REGISTRY_PATH)


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------

class TestPresentationSpecModel:
    def test_minimal_spec_valid(self):
        spec = PresentationSpec(title="T", subtitle="S")
        assert spec.title == "T"
        assert spec.template == "ops_review_v1"
        assert spec.sections == []

    def test_defaults(self):
        spec = PresentationSpec(title="T", subtitle="S")
        assert spec.author == "Unknown"

    def test_extra_field_forbidden(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PresentationSpec(title="T", subtitle="S", unknown_field="x")

    def test_section_with_bullets(self):
        s = SectionSpec(title="Sec", bullets=["A", "B"])
        assert s.bullets == ["A", "B"]

    def test_metric_spec(self):
        m = MetricSpec(label="Uptime", value="99.9", unit="%")
        assert m.unit == "%"

    def test_image_spec(self):
        i = ImageSpec(path="assets/img.png", caption="Overview")
        assert i.title is None


# ---------------------------------------------------------------------------
# Translator: structure
# ---------------------------------------------------------------------------

class TestConvertSpecToDeck:
    @pytest.fixture
    def simple_spec(self):
        return PresentationSpec(
            title="Test Deck",
            subtitle="Subtitle Here",
            author="Tester",
            sections=[
                SectionSpec(title="Section One", bullets=["Bullet A", "Bullet B"]),
            ],
        )

    def test_deck_metadata_title(self, simple_spec):
        result = convert_spec_to_deck(simple_spec)
        assert result["deck"]["title"] == "Test Deck"

    def test_deck_metadata_template(self, simple_spec):
        result = convert_spec_to_deck(simple_spec)
        assert result["deck"]["template"] == "ops_review_v1"

    def test_first_slide_is_title(self, simple_spec):
        result = convert_spec_to_deck(simple_spec)
        assert result["slides"][0]["type"] == "title"
        assert result["slides"][0]["title"] == "Test Deck"

    def test_section_divider_emitted(self, simple_spec):
        slides = convert_spec_to_deck(simple_spec)["slides"]
        types = [s["type"] for s in slides]
        assert "section" in types

    def test_bullets_slide_emitted(self, simple_spec):
        slides = convert_spec_to_deck(simple_spec)["slides"]
        bullets_slides = [s for s in slides if s["type"] == "bullets"]
        assert len(bullets_slides) == 1
        assert "Bullet A" in bullets_slides[0]["bullets"]

    def test_no_section_divider_when_disabled(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="X", bullets=["Y"], include_section_divider=False)],
        )
        slides = convert_spec_to_deck(spec)["slides"]
        assert all(s["type"] != "section" for s in slides)

    def test_metrics_become_metric_summary(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(
                    title="KPIs",
                    metrics=[
                        MetricSpec(label="A", value="1"),
                        MetricSpec(label="B", value="2"),
                    ],
                )
            ],
        )
        slides = convert_spec_to_deck(spec)["slides"]
        metric_slides = [s for s in slides if s["type"] == "metric_summary"]
        assert len(metric_slides) == 1
        assert len(metric_slides[0]["metrics"]) == 2

    def test_metrics_split_at_4(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(
                    title="Many KPIs",
                    metrics=[MetricSpec(label=f"M{i}", value=str(i)) for i in range(5)],
                )
            ],
        )
        slides = convert_spec_to_deck(spec)["slides"]
        metric_slides = [s for s in slides if s["type"] == "metric_summary"]
        assert len(metric_slides) == 2
        assert len(metric_slides[0]["metrics"]) == 4
        assert len(metric_slides[1]["metrics"]) == 1

    def test_bullets_split_at_6(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="Long", bullets=[f"B{i}" for i in range(7)])],
        )
        slides = convert_spec_to_deck(spec)["slides"]
        bullet_slides = [s for s in slides if s["type"] == "bullets"]
        assert len(bullet_slides) == 2
        assert len(bullet_slides[0]["bullets"]) == 6
        assert len(bullet_slides[1]["bullets"]) == 1

    def test_image_becomes_image_caption(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(
                    title="Arch",
                    images=[ImageSpec(path="assets/img.png", caption="The diagram")],
                )
            ],
        )
        slides = convert_spec_to_deck(spec)["slides"]
        img_slides = [s for s in slides if s["type"] == "image_caption"]
        assert len(img_slides) == 1
        assert img_slides[0]["image_path"] == "assets/img.png"
        assert img_slides[0]["caption"] == "The diagram"

    def test_image_title_defaults_to_section_title(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(
                    title="Section X",
                    images=[ImageSpec(path="p.png", caption="cap")],
                )
            ],
        )
        slides = convert_spec_to_deck(spec)["slides"]
        img_slide = next(s for s in slides if s["type"] == "image_caption")
        assert img_slide["title"] == "Section X"

    def test_image_title_override(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(
                    title="Section X",
                    images=[ImageSpec(path="p.png", caption="cap", title="Custom Title")],
                )
            ],
        )
        slides = convert_spec_to_deck(spec)["slides"]
        img_slide = next(s for s in slides if s["type"] == "image_caption")
        assert img_slide["title"] == "Custom Title"


# ---------------------------------------------------------------------------
# End-to-end: spec → deck dict → validate_deck
# ---------------------------------------------------------------------------

class TestSpecEndToEnd:
    @pytest.fixture
    def full_spec(self):
        return PresentationSpec(
            title="Q2 Engineering Update",
            subtitle="Analytics Platform Team",
            author="Test Author",
            template="ops_review_v1",
            sections=[
                SectionSpec(
                    title="Delivery Highlights",
                    bullets=["Shipped pptgen v1", "Onboarded 4 teams"],
                ),
                SectionSpec(
                    title="Platform Metrics",
                    metrics=[
                        MetricSpec(label="Decks Generated", value="47"),
                        MetricSpec(label="Avg Build Time", value="3", unit=" sec"),
                    ],
                ),
                SectionSpec(
                    title="Architecture",
                    images=[
                        ImageSpec(
                            path="assets/architecture.png",
                            caption="pptgen system architecture",
                        ),
                    ],
                ),
            ],
        )

    def test_generated_deck_passes_validation(self, full_spec, registry, tmp_path):
        deck_dict = convert_spec_to_deck(full_spec)
        yaml_path = tmp_path / "spec_deck.yaml"
        yaml_path.write_text(
            yaml.dump(deck_dict, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        deck, raw = load_deck(yaml_path)
        result = validate_deck(deck, registry, raw)
        assert result.valid, "\n".join(result.errors)

    def test_generated_slide_count(self, full_spec, tmp_path):
        deck_dict = convert_spec_to_deck(full_spec)
        yaml_path = tmp_path / "spec_deck.yaml"
        yaml_path.write_text(
            yaml.dump(deck_dict, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        deck, _ = load_deck(yaml_path)
        # title + (section+bullets) + (section+metrics) + (section+image) = 7 slides
        assert len(deck.slides) == 7

    def test_empty_spec_produces_title_only(self, registry, tmp_path):
        spec = PresentationSpec(title="Minimal", subtitle="Sub")
        deck_dict = convert_spec_to_deck(spec)
        yaml_path = tmp_path / "minimal.yaml"
        yaml_path.write_text(
            yaml.dump(deck_dict, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        deck, raw = load_deck(yaml_path)
        result = validate_deck(deck, registry, raw)
        assert result.valid
        assert len(deck.slides) == 1
        assert deck.slides[0].type == "title"
