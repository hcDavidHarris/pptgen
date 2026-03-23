"""Unit tests for the transcript connector."""

from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.connectors import ConnectorOutput
from pptgen.connectors.transcript_connector import TranscriptConnector
from pptgen.input_router import route_input


_FIXTURES = Path(__file__).parent.parent / "fixtures"
_TRANSCRIPT = _FIXTURES / "transcript.txt"


class TestTranscriptConnectorBasics:
    def test_returns_connector_output(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        assert isinstance(out, ConnectorOutput)

    def test_text_is_non_empty(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        assert out.text.strip()

    def test_metadata_is_dict(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        assert isinstance(out.metadata, dict)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TranscriptConnector().normalize(tmp_path / "no_such_file.txt")


class TestTranscriptNormalization:
    def test_attendees_in_text(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        assert "Attendees" in out.text

    def test_timestamps_stripped_from_text(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        # Timestamp patterns like [00:00] should not appear
        assert "[00:" not in out.text

    def test_action_items_preserved(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        # The word "action" should survive normalization
        assert "action" in out.text.lower() or "Action" in out.text

    def test_meeting_header_preserved(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        assert "Meeting" in out.text

    def test_no_blank_lines_in_output(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        for line in out.text.splitlines():
            # Every line in the output should be non-empty
            assert line.strip()

    def test_metadata_contains_speakers(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        assert "speakers" in out.metadata or "attendees" in out.metadata

    def test_deterministic(self):
        c = TranscriptConnector()
        out1 = c.normalize(_TRANSCRIPT)
        out2 = c.normalize(_TRANSCRIPT)
        assert out1.text == out2.text


class TestTranscriptConnectorInlineInput:
    """Test with a small inline fixture to isolate specific behaviors."""

    def _write(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "t.txt"
        p.write_text(content, encoding="utf-8")
        return p

    def test_strips_empty_lines(self, tmp_path):
        p = self._write(tmp_path, "Meeting: Test\n\n\nAlice: Hello\n\n")
        out = TranscriptConnector().normalize(p)
        for line in out.text.splitlines():
            assert line.strip()

    def test_removes_timestamp_prefix(self, tmp_path):
        p = self._write(tmp_path, "[01:23] Bob: Important point here.\n")
        out = TranscriptConnector().normalize(p)
        assert "[01:23]" not in out.text
        assert "Important point here" in out.text

    def test_extracts_attendees_from_header(self, tmp_path):
        p = self._write(tmp_path, "Attendees: Alice, Bob, Carol\nSome content here.\n")
        out = TranscriptConnector().normalize(p)
        assert "Alice" in out.text
        assert "attendees" in out.metadata or "speakers" in out.metadata


class TestTranscriptRouting:
    def test_routes_to_meeting_notes(self):
        out = TranscriptConnector().normalize(_TRANSCRIPT)
        assert route_input(out.text) == "meeting-notes-to-eos-rocks"
